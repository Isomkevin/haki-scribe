"""
Connectors API — list, connect (verify), disconnect, and export documents
to connected storage providers. Also extends the LLM model picker with
connected provider keys.
"""

import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import ActionResult
from app.services import action_executor, integrations, storage, trigger_client
from app.integrations import llm_client

router = APIRouter()


class ConnectRequest(BaseModel):
    credentials: dict[str, Any]


class ExportRequest(BaseModel):
    provider: str  # "google_drive" | "dropbox" | "onedrive"


@router.get("", response_model=list[dict[str, Any]])
def list_integrations():
    return integrations.list_connections()


@router.post("/{provider_id}")
async def connect_integration(provider_id: str, payload: ConnectRequest):
    definition = integrations.provider_def(provider_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    creds = {k: str(v).strip() for k, v in payload.credentials.items() if str(v).strip()}
    if not creds:
        raise HTTPException(status_code=400, detail="No credentials provided")

    result = await integrations.verify(provider_id, creds)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error") or "Verification failed")

    integrations.save_connection(provider_id, creds)
    return {
        "provider_id": provider_id,
        "name": definition["name"],
        "connected": True,
        "connected_at": integrations.get_connection(provider_id).get("connected_at"),
        "masked_creds": integrations._mask_creds(provider_id, creds),
    }


@router.delete("/{provider_id}")
def disconnect_integration(provider_id: str):
    if not integrations.remove_connection(provider_id):
        raise HTTPException(status_code=404, detail="Provider not connected")
    return {"provider_id": provider_id, "connected": False}


@router.post("/{session_id}/documents/{action_id}/export")
async def export_document(session_id: uuid.UUID, action_id: uuid.UUID, payload: ExportRequest):
    """Export a generated document to a connected storage provider.
    Reads the already-generated ActionResult text from storage — the
    export payload is the artifact, never the raw transcript."""
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the action result
    result: Optional[ActionResult] = None
    for item in detail.action_results:
        if item.action_id == action_id:
            result = item
            break
    if result is None or result.status != "success":
        raise HTTPException(status_code=404, detail="Generated document not found")

    text = result.result.get("document_text") if isinstance(result.result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=400, detail="This action has no document text to export")

    title = result.result.get("document_kind") or result.type.value
    export = await integrations.export_document(payload.provider, text, str(title).replace(" ", "-"))

    if export["ok"]:
        # Record the export on the result
        result.result.setdefault("exports", [])
        export_record = {"provider": payload.provider, "url": export.get("url")}
        result.result["exports"].append(export_record)
        storage.upsert_action_results(session_id, [result])
        return {"ok": True, "url": export.get("url"), "provider": payload.provider}

    raise HTTPException(status_code=400, detail=export.get("error") or "Export failed")
