"""Reconcile HakiChain webhook events into local hearings/matters (Phase 2)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.models.schemas import HearingStatus
from app.services import hearings as hearings_service
from app.services import storage

logger = logging.getLogger(__name__)

# In-memory delivery de-dupe for demo mode (production should use a table).
_seen_deliveries: set[str] = set()


def webhook_secret() -> str:
    return (os.environ.get("HAKICHAIN_WEBHOOK_SECRET") or os.environ.get("HAKISCRIBE_WEBHOOK_SIGNING_SECRET") or "").strip()


def verify_signature(*, signature_header: str, body: bytes) -> bool:
    secret = webhook_secret()
    if not secret:
        # Fail closed in production-shaped envs; allow demo when unset.
        if os.environ.get("HAKISCRIBE_PRODUCTION_AUTH", "").lower() == "true":
            return False
        return True
    provided = (signature_header or "").strip()
    if provided.startswith("sha256="):
        provided = provided[7:]
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, provided)


def _mark_delivery(delivery_id: str | None) -> bool:
    """Return False if already processed (idempotent)."""
    if not delivery_id:
        return True
    if delivery_id in _seen_deliveries:
        return False
    _seen_deliveries.add(delivery_id)
    if len(_seen_deliveries) > 5000:
        # Bound memory; oldest-ish drop by clearing half.
        for key in list(_seen_deliveries)[:2500]:
            _seen_deliveries.discard(key)
    return True


def apply_event(event: str, data: dict[str, Any], *, delivery_id: str | None = None) -> dict[str, Any]:
    if not _mark_delivery(delivery_id):
        return {"ok": True, "reused": True, "event": event}

    if event == "matter.updated":
        return _apply_matter_updated(data)
    if event in ("hearing.scheduled", "hearing.cancelled", "hearing.filed"):
        return _apply_hearing_event(event, data)
    logger.info("Ignoring unknown HakiChain event %s", event)
    return {"ok": True, "ignored": True, "event": event}


def _apply_matter_updated(data: dict[str, Any]) -> dict[str, Any]:
    workspace_id = str(data.get("workspace_id") or "").strip()
    client_id = str(data.get("client_id") or "").strip()
    if not workspace_id and not client_id:
        return {"ok": False, "error": "workspace_id or client_id required"}
    matched = 0
    for matter in storage.list_matters():
        if (workspace_id and matter.hakichain_workspace_id == workspace_id) or (
            client_id and matter.hakichain_client_id == client_id
        ):
            if workspace_id:
                matter.hakichain_workspace_id = workspace_id
            if client_id:
                matter.hakichain_client_id = client_id
            matter.hakichain_linked_at = datetime.utcnow()
            matched += 1
    if matched:
        storage._persist()  # noqa: SLF001
    return {"ok": True, "event": "matter.updated", "matters_touched": matched}


def _apply_hearing_event(event: str, data: dict[str, Any]) -> dict[str, Any]:
    scribe_id = str(data.get("scribe_hearing_id") or "").strip()
    if not scribe_id:
        return {"ok": False, "error": "scribe_hearing_id required"}
    try:
        hearing_uuid = UUID(scribe_id)
    except ValueError:
        return {"ok": False, "error": "scribe_hearing_id must be a UUID"}
    hearing = hearings_service.get_hearing(hearing_uuid)
    if hearing is None:
        return {"ok": True, "skipped": "hearing_not_local", "scribe_hearing_id": scribe_id}

    status = str(data.get("status") or "").strip()
    meta = dict(hearing.platform_metadata or {})
    sync = dict(meta.get("hakichain_sync") or {})
    sync.update(
        {
            "last_event": event,
            "remote_hearing_id": data.get("hearing_id"),
            "workspace_id": data.get("workspace_id"),
            "client_id": data.get("client_id"),
            "synced_at": datetime.utcnow().isoformat(),
        }
    )
    meta["hakichain_sync"] = sync
    hearing.platform_metadata = meta

    if event == "hearing.cancelled" and hearing.status not in (HearingStatus.filed, HearingStatus.rejected):
        try:
            hearings_service.transition(hearing, HearingStatus.rejected)
        except hearings_service.InvalidTransition:
            hearing.status = HearingStatus.rejected
            hearing.updated_at = datetime.utcnow()
    elif event == "hearing.filed" and hearing.status == HearingStatus.reviewed:
        try:
            hearings_service.transition(hearing, HearingStatus.filed)
        except hearings_service.InvalidTransition:
            pass
    elif status and event == "hearing.scheduled":
        # Soft sync only — do not invent transitions that would confuse the local lifecycle.
        pass

    hearings_service._save()  # noqa: SLF001
    return {"ok": True, "event": event, "hearing_id": str(hearing.id), "status": hearing.status.value}

