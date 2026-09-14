"""Omi wearable ingress.

Supports:
1. Legacy paste pairing — ``?session_id=<HakiScribe UUID>``
2. Miniapp path — ``?uid=<omi-user>`` (and Omi's own session_id), after
   the lawyer completes ``/integrations/omi/auth``

Accepted shapes (official Omi + our seed script):
- POST body array of segments (realtime)
- {session_id, segments}
- {session_external_id, segments}
- {id, transcript_segments, structured} memory webhook
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.models.schemas import SessionStatus, TranscriptSegment
from app.services import omi_pairing, storage

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


def _extract_payload(
    body: Any, query_session_id: str | None
) -> tuple[str | None, list[dict[str, Any]], str | None, bool]:
    """Returns session_ref, segments, memory_title, is_memory."""
    session_ref = query_session_id
    segments: list[Any] = []
    memory_title: str | None = None
    is_memory = False

    if isinstance(body, list):
        segments = body
    elif isinstance(body, dict):
        # Prefer query session_id; body may carry Omi's conversation id.
        session_ref = query_session_id or body.get("session_external_id") or body.get("session_id") or body.get("id")
        structured = body.get("structured") if isinstance(body.get("structured"), dict) else {}
        if structured.get("title"):
            memory_title = str(structured["title"]).strip() or None
        segments = (
            body.get("segments")
            or body.get("transcript_segments")
            or body.get("transcriptSegments")
            or []
        )
        is_memory = bool(
            body.get("transcript_segments") is not None
            or body.get("transcriptSegments") is not None
            or structured
            or body.get("finished_at")
        )
        if not segments and isinstance(body.get("transcript"), str) and body["transcript"].strip():
            segments = [{"text": body["transcript"], "start": 0, "end": 0}]
    else:
        raise HTTPException(status_code=400, detail="Omi webhook body must be a JSON object or array")

    if not isinstance(segments, list):
        raise HTTPException(status_code=400, detail="segments must be a list")
    return (str(session_ref) if session_ref else None), _normalize_segments(segments), memory_title, is_memory


def _check_secret(*, uid: str | None, x_omi_secret: str) -> None:
    if not OMI_SHARED_SECRET:
        return
    # Miniapp posts with a linked uid do not send x-omi-secret.
    if uid and omi_pairing.is_linked(uid):
        if x_omi_secret and x_omi_secret != OMI_SHARED_SECRET:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        return
    if x_omi_secret != OMI_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/omi")
async def receive_omi_transcript(
    request: Request,
    session_id: str | None = Query(default=None),
    uid: str | None = Query(default=None),
    x_omi_secret: str = Header(default=""),
):
    cleaned_uid = (uid or "").strip() or None
    _check_secret(uid=cleaned_uid, x_omi_secret=x_omi_secret)

    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    session_ref, segments, memory_title, is_memory = _extract_payload(body, session_id)

    try:
        session = omi_pairing.resolve_session(
            session_ref=session_ref,
            uid=cleaned_uid,
            memory_title=memory_title,
            is_memory=is_memory and bool(cleaned_uid),
        )
    except omi_pairing.OmiPairingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None

    for raw in segments:
        source_raw = {**(raw["source_raw"] or {})}
        if cleaned_uid:
            source_raw["omi_uid"] = cleaned_uid
        if session_ref:
            source_raw["omi_session_id"] = session_ref
        storage.append_segment(
            session.id,
            TranscriptSegment(
                session_id=session.id,
                speaker=raw["speaker"],
                text=raw["text"],
                start_ms=raw["start_ms"],
                end_ms=raw["end_ms"],
                confidence=raw["confidence"],
                source_raw=source_raw,
            ),
        )

    if is_memory and cleaned_uid and session.status == SessionStatus.recording:
        storage.update_session_status(session.id, SessionStatus.ready)

    # Omi realtime apps expect session_id echoed back (HakiScribe UUID).
    return {"session_id": str(session.id), "received": len(segments), "uid": cleaned_uid}
