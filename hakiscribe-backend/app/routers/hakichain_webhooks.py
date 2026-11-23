"""Inbound HakiChain → HakiScribe webhooks (Phase 2)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.services import hakichain_sync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/hakichain")
async def hakichain_webhook(
    request: Request,
    x_hakichain_signature: str | None = Header(default=None, alias="X-HakiChain-Signature"),
    x_hakichain_event: str | None = Header(default=None, alias="X-HakiChain-Event"),
    x_hakichain_delivery: str | None = Header(default=None, alias="X-HakiChain-Delivery"),
):
    body = await request.body()
    if not hakichain_sync.verify_signature(signature_header=x_hakichain_signature or "", body=body):
        raise HTTPException(status_code=401, detail="Invalid HakiChain webhook signature")

    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event = str(payload.get("event") or x_hakichain_event or "").strip()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not event:
        raise HTTPException(status_code=400, detail="event required")

    result = hakichain_sync.apply_event(event, data, delivery_id=x_hakichain_delivery)
    logger.info("HakiChain webhook %s → %s", event, result)
    return result


@router.post("/hakichain/reconcile")
async def hakichain_reconcile():
    """Best-effort pull of HakiChain matters to refresh local FKs."""
    from app.integrations import hakichain_client

    if not hakichain_client.configured():
        raise HTTPException(status_code=400, detail="HakiChain is not connected")
    result = await hakichain_client.list_matters()
    if result is None:
        raise HTTPException(status_code=502, detail=hakichain_client.last_error() or "list_matters failed")

    from datetime import datetime

    from app.services import storage

    remote = {str(m.get("workspace_id")): m for m in (result.get("matters") or [])}
    touched = 0
    for matter in storage.list_matters():
        wid = matter.hakichain_workspace_id
        if not wid or wid not in remote:
            continue
        row = remote[wid]
        matter.hakichain_client_id = str(row.get("client_id") or matter.hakichain_client_id or "")
        matter.hakichain_linked_at = datetime.utcnow()
        touched += 1
    if touched:
        storage._persist()  # noqa: SLF001
    return {"ok": True, "matters_refreshed": touched, "remote_count": len(remote)}
