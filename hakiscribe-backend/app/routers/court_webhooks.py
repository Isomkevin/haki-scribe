"""Virtual court platform webhooks.

POST /webhooks/zoom — Zoom Event Subscriptions:
  endpoint.url_validation → challenge response (required to save the endpoint)
  recording.completed     → upsert hearing, propose matter matches, download the
                            recording with the event's download_token, ingest

Fails closed: without ZOOM_WEBHOOK_SECRET_TOKEN every request is rejected.
The matter link still needs a human confirm before the hearing is processed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.models.schemas import HearingCreate, HearingSource
from app.services import hearing_pipeline
from app.services import hearings as hearings_service
from app.services.court_adapters import zoom_adapter

logger = logging.getLogger(__name__)

router = APIRouter()


async def _ingest_zoom_recording(hearing_id, files: list[dict[str, Any]], download_token: str, meeting: dict[str, Any]) -> None:
    try:
        artifact = await zoom_adapter.download_preferred(files, download_token, prefer="audio", meeting=meeting)
        if artifact.kind == "transcript":
            hearing_pipeline.ingest_transcript(hearing_id, artifact.data.decode("utf-8", errors="replace"), origin="zoom")
        else:
            hearing_pipeline.ingest_recording(hearing_id, artifact.filename, artifact.data, artifact.content_type)
        hearings_service.set_pipeline_state(hearing_id, state="ingested", step="zoom_webhook", error=None)
    except Exception as exc:  # noqa: BLE001 — recorded for the UI; Zoom already got its 200
        logger.warning("Zoom recording ingest failed for hearing %s: %s", hearing_id, exc)
        hearings_service.set_pipeline_state(hearing_id, state="error", step="zoom_webhook", error=str(exc)[:500])


@router.post("/zoom")
async def zoom_webhook(request: Request, background_tasks: BackgroundTasks):
    secret = zoom_adapter.webhook_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="ZOOM_WEBHOOK_SECRET_TOKEN is not configured")
    body = await request.body()
    try:
        event = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON") from None
    payload = event.get("payload") or {}

    # Zoom's URL validation event is unsigned by design; it proves we hold the secret.
    if event.get("event") == "endpoint.url_validation":
        plain = str(payload.get("plainToken") or "")
        if not plain:
            raise HTTPException(status_code=400, detail="plainToken missing")
        return {"plainToken": plain, "encryptedToken": zoom_adapter.sign(secret, plain)}

    if not zoom_adapter.verify_webhook(
        secret,
        signature=request.headers.get("x-zm-signature", ""),
        timestamp=request.headers.get("x-zm-request-timestamp", ""),
        body=body,
    ):
        raise HTTPException(status_code=401, detail="invalid Zoom signature")

    if event.get("event") != "recording.completed":
        return {"status": "ignored", "event": event.get("event")}

    obj = payload.get("object") or {}
    meeting_id = str(obj.get("id") or "")
    if not meeting_id:
        raise HTTPException(status_code=400, detail="recording event has no meeting id")
    hearing = hearings_service.upsert_external(
        HearingCreate(
            source=HearingSource.zoom,
            external_id=meeting_id,
            title=str(obj.get("topic") or "Zoom hearing"),
            starts_at=zoom_adapter._parse(obj.get("start_time")),
            platform_metadata={"zoom": {"uuid": obj.get("uuid"), "host_id": obj.get("host_id")}},
        )
    )
    hearings_service.propose_matches(hearing.id)
    download_token = str(event.get("download_token") or "")
    if not download_token:
        hearings_service.set_pipeline_state(hearing.id, state="error", step="zoom_webhook", error="event carried no download_token")
        return {"status": "accepted", "hearing_id": str(hearing.id), "ingest": "skipped"}
    background_tasks.add_task(_ingest_zoom_recording, hearing.id, obj.get("recording_files") or [], download_token, obj)
    return {"status": "accepted", "hearing_id": str(hearing.id), "ingest": "queued"}
