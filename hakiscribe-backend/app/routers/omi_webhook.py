"""Omi wearable ingress.

Omi POSTs live transcript segments (or a finished memory) to this URL.
Pairing is via `?session_id=<HakiScribe UUID>` so a lawyer can open a
session on their phone, paste the webhook into Omi, and keep looking at
the client — the room is the capture surface, not a chat box.

Accepted shapes (official Omi + our seed script):
- POST body array of segments
- {session_id, segments}
- {session_external_id, segments}
- {id, transcript_segments} memory webhook
Query `session_id` wins when present.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.models.schemas import TranscriptSegment
from app.services import storage

router = APIRouter()

OMI_SHARED_SECRET = os.environ.get("OMI_SHARED_SECRET", "")


def _as_ms(value: Any, *, seconds_fallback: Any = None) -> int:
    if value is not None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        # Omi uses seconds; our store and seed script use milliseconds.
        return int(number if number >= 1000 else number * 1000)
    if seconds_fallback is not None:
        try:
            return int(float(seconds_fallback) * 1000)
        except (TypeError, ValueError):
            return 0
    return 0


def _speaker(raw: dict[str, Any]) -> str | None:
    for key in ("speaker_name", "speaker", "Speaker"):
        value = raw.get(key)
        if value:
            label = str(value)
            if label.upper().startswith("SPEAKER_"):
                try:
                    index = int(label.split("_", 1)[1]) + 1
                except ValueError:
                    return label
                return f"Speaker {index}"
            return label
    speaker_id = raw.get("speakerId") if raw.get("speakerId") is not None else raw.get("speaker_id")
    if speaker_id is not None:
        try:
            return f"Speaker {int(speaker_id) + 1}"
        except (TypeError, ValueError):
            return None
    return None


def _normalize_segments(raw_segments: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or raw.get("transcript") or "").strip()
        if not text:
            continue
        normalized.append(
            {
                "speaker": _speaker(raw),
                "text": text,
                "start_ms": _as_ms(raw.get("start_ms"), seconds_fallback=raw.get("start")),
                "end_ms": _as_ms(raw.get("end_ms"), seconds_fallback=raw.get("end")),
                "confidence": raw.get("confidence"),
                "source_raw": raw,
            }
        )
    return normalized


def _extract_payload(body: Any, query_session_id: str | None) -> tuple[str | None, list[dict[str, Any]]]:
    session_ref = query_session_id
    segments: list[Any] = []

    if isinstance(body, list):
        segments = body
    elif isinstance(body, dict):
        session_ref = (
            query_session_id
            or body.get("session_external_id")
            or body.get("session_id")
            or None
        )
        segments = (
            body.get("segments")
            or body.get("transcript_segments")
            or body.get("transcriptSegments")
            or []
        )
        if not segments and isinstance(body.get("transcript"), str) and body["transcript"].strip():
            segments = [{"text": body["transcript"], "start": 0, "end": 0}]
    else:
        raise HTTPException(status_code=400, detail="Omi webhook body must be a JSON object or array")

    if not isinstance(segments, list):
        raise HTTPException(status_code=400, detail="segments must be a list")
    return str(session_ref) if session_ref else None, _normalize_segments(segments)


@router.post("/omi")
async def receive_omi_transcript(
    request: Request,
    session_id: str | None = Query(default=None),
    uid: str | None = Query(default=None),
    x_omi_secret: str = Header(default=""),
):
    if OMI_SHARED_SECRET and x_omi_secret != OMI_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    session_ref, segments = _extract_payload(body, session_id)
    if session_ref is None:
        raise HTTPException(
            status_code=400,
            detail="Missing session_id. Pair Omi with /webhooks/omi?session_id=<HakiScribe session UUID>.",
        )

    try:
        resolved = uuid.UUID(session_ref)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id must be a HakiScribe session UUID") from None

    detail = storage.get_session(resolved)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")

    for raw in segments:
        storage.append_segment(
            resolved,
            TranscriptSegment(
                session_id=resolved,
                speaker=raw["speaker"],
                text=raw["text"],
                start_ms=raw["start_ms"],
                end_ms=raw["end_ms"],
                confidence=raw["confidence"],
                source_raw={**(raw["source_raw"] or {}), "omi_uid": uid} if uid else raw["source_raw"],
            ),
        )

    # Omi realtime apps expect session_id echoed back.
    return {"session_id": str(resolved), "received": len(segments), "uid": uid}
