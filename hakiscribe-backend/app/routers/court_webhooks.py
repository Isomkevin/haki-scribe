"""Virtual court platform webhooks.

POST /webhooks/zoom — Zoom Event Subscriptions:
  endpoint.url_validation → challenge response (required to save the endpoint)
  recording.completed     → upsert hearing, propose matter matches, download the
                            recording with the event's download_token, ingest

Fails closed: without ZOOM_WEBHOOK_SECRET_TOKEN every request is rejected.
The matter link still needs a human confirm before the hearing is processed.

Multi-tenant (production auth): resolve organisation from ZOOM_HOST_ORG_MAP
(host_id / account_id → org UUID) or ZOOM_DEFAULT_ORGANISATION_ID. Unsigned
or unscoped events are rejected.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.models.schemas import HearingCreate, HearingSource
from app.services import hearing_pipeline
from app.services import hearings as hearings_service
from app.services.court_adapters import zoom_adapter

logger = logging.getLogger(__name__)

router = APIRouter()

_PRODUCTION = os.environ.get("HAKISCRIBE_PRODUCTION_AUTH", "false").lower() == "true"


async def _ingest_zoom_recording(
    hearing_id,
    files: list[dict[str, Any]],
    download_token: str,
    meeting: dict[str, Any],
    *,
    store: Any = None,
) -> None:
    store = store or hearings_service
    try:
        artifact = await zoom_adapter.download_preferred(files, download_token, prefer="audio", meeting=meeting)
        if artifact.kind == "transcript":
            hearing_pipeline.ingest_transcript(
                hearing_id, artifact.data.decode("utf-8", errors="replace"), origin="zoom", store=store
            )
        else:
            hearing_pipeline.ingest_recording(
                hearing_id, artifact.filename, artifact.data, artifact.content_type, store=store
            )
        store.set_pipeline_state(hearing_id, state="ingested", step="zoom_webhook", error=None)
    except Exception as exc:  # noqa: BLE001 — recorded for the UI; Zoom already got its 200
        logger.warning("Zoom recording ingest failed for hearing %s: %s", hearing_id, exc)
        store.set_pipeline_state(hearing_id, state="error", step="zoom_webhook", error=str(exc)[:500])


def _production_repo(organisation_id: UUID):
    from app.services.production_hearings import ProductionHearingsRepo
    from app.services.tenant_context import production_client

    return ProductionHearingsRepo(production_client(), organisation_id)


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

    store: Any = hearings_service
    org_id = None
    if _PRODUCTION:
        from app.services.production_hearings import resolve_zoom_organisation

        org_id = resolve_zoom_organisation(
            str(obj.get("host_id") or "") or None,
            str(payload.get("account_id") or obj.get("account_id") or "") or None,
        )
        if org_id is None:
            raise HTTPException(
                status_code=403,
                detail="Zoom event has no organisation mapping (set ZOOM_HOST_ORG_MAP or ZOOM_DEFAULT_ORGANISATION_ID)",
            )
        store = _production_repo(org_id)

    hearing = store.upsert_external(
        HearingCreate(
            source=HearingSource.zoom,
            external_id=meeting_id,
            title=str(obj.get("topic") or "Zoom hearing"),
            starts_at=zoom_adapter._parse(obj.get("start_time")),
            platform_metadata={
                "zoom": {
                    "uuid": obj.get("uuid"),
                    "host_id": obj.get("host_id"),
                    "organisation_id": str(org_id) if org_id else None,
                }
            },
        )
    )
    store.propose_matches(hearing.id)
    download_token = str(event.get("download_token") or "")
    if not download_token:
        store.set_pipeline_state(hearing.id, state="error", step="zoom_webhook", error="event carried no download_token")
        return {"status": "accepted", "hearing_id": str(hearing.id), "ingest": "skipped"}
    background_tasks.add_task(
        _ingest_zoom_recording,
        hearing.id,
        obj.get("recording_files") or [],
        download_token,
        obj,
        store=store,
    )
    return {
        "status": "accepted",
        "hearing_id": str(hearing.id),
        "organisation_id": str(org_id) if org_id else None,
        "ingest": "queued",
    }


@router.post("/teams-bot/calls")
async def teams_bot_callback(request: Request):
    """Bot Framework / Graph calling notifications (media lifecycle)."""
    # Always acknowledge; media ingestion is handled by the bot worker when configured.
    body = await request.body()
    try:
        event = json.loads(body or b"{}")
    except json.JSONDecodeError:
        event = {}
    logger.info("Teams bot callback: %s", (event.get("@odata.type") or event.get("type") or "unknown"))
    return {"status": "ok"}
