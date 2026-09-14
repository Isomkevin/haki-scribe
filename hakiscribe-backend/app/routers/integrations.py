"""
Connectors API — list, connect (verify), disconnect, and export documents
to connected storage providers. Omi Miniapp auth / setup-completed live here.
"""

import os
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.models.schemas import ActionResult
from app.services import integrations, omi_pairing, storage

router = APIRouter()


class ConnectRequest(BaseModel):
    credentials: dict[str, Any]


class ExportRequest(BaseModel):
    provider: str  # "google_drive" | "dropbox" | "onedrive"


@router.get("", response_model=list[dict[str, Any]])
def list_integrations():
    return integrations.list_connections()


@router.get("/omi/status")
def omi_status():
    return omi_pairing.status_payload()


@router.get("/omi/setup-completed")
def omi_setup_completed(uid: str | None = Query(default=None)):
    return {"is_setup_completed": omi_pairing.setup_completed(uid)}


@router.get("/omi/auth", response_class=HTMLResponse)
def omi_auth(uid: str | None = Query(default=None)):
    if not uid or not str(uid).strip():
        return HTMLResponse(
            status_code=400,
            content=_omi_html(
                title="Missing uid",
                body="Omi must open this URL with a <code>uid</code> query parameter.",
                ok=False,
            ),
        )
    try:
        omi_pairing.link_uid(str(uid).strip())
    except omi_pairing.OmiPairingError as exc:
        return HTMLResponse(
            status_code=exc.status_code,
            content=_omi_html(title="Could not link Omi", body=exc.message, ok=False),
        )
    return HTMLResponse(
        content=_omi_html(
            title="HakiScribe is linked",
            body="Return to Omi. Live transcripts and finished memories will appear on the desk.",
            ok=True,
        )
    )


def _omi_html(*, title: str, body: str, ok: bool) -> str:
    accent = "#1f4d3a" if ok else "#8b2e2e"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · HakiScribe</title>
  <style>
    body {{ font-family: Georgia, "Times New Roman", serif; background: #f4f1ea; color: #1a1a1a;
      margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 1.5rem; }}
    main {{ max-width: 28rem; background: #fff; border: 1px solid #d9d2c5; border-radius: 12px;
      padding: 1.75rem 1.5rem; box-shadow: 0 8px 24px rgba(31, 77, 58, 0.08); }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.75rem; color: {accent}; }}
    p {{ margin: 0; line-height: 1.55; color: #444; font-family: system-ui, sans-serif; font-size: 0.95rem; }}
    code {{ font-size: 0.85em; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{body}</p>
  </main>
</body>
</html>"""


@router.post("/{provider_id}")
async def connect_integration(provider_id: str, payload: ConnectRequest):
    definition = integrations.provider_def(provider_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    creds = {k: str(v).strip() for k, v in payload.credentials.items() if str(v).strip()}
    if provider_id == "openrouter" and "default_model" not in creds:
        creds["default_model"] = os.environ.get("ASK_MODEL") or "openai/gpt-4o"
    if not creds:
        raise HTTPException(status_code=400, detail="No credentials provided")
    if provider_id in {"anthropic", "openai", "gemini", "mistral", "openrouter"} and not creds.get("api_key"):
        raise HTTPException(status_code=400, detail="No credentials provided")
    if provider_id == "omi" and not creds.get("uid"):
        raise HTTPException(status_code=400, detail="Missing Omi uid")

    result = await integrations.verify(provider_id, creds)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result.get("error") or "Verification failed")

    if provider_id == "omi":
        omi_pairing.link_uid(str(creds["uid"]))
    else:
        integrations.save_connection(provider_id, creds)

    connection = integrations.get_connection(provider_id) or {}
    return {
        "provider_id": provider_id,
        "name": definition["name"],
        "connected": True,
        "connected_at": connection.get("connected_at"),
        "masked_creds": integrations._mask_creds(provider_id, connection.get("creds") or creds),
    }


@router.delete("/{provider_id}")
def disconnect_integration(provider_id: str):
    if provider_id == "omi":
        if not omi_pairing.linked_uid():
            raise HTTPException(status_code=404, detail="Provider not connected")
        omi_pairing.unlink()
        return {"provider_id": provider_id, "connected": False}

    if not integrations.can_disconnect(provider_id):
        if integrations.get_connection(provider_id):
            raise HTTPException(
                status_code=400,
                detail="This connector uses the workspace key. Remove OPENROUTER_API_KEY (or the matching env var) to disconnect it.",
            )
        raise HTTPException(status_code=404, detail="Provider not connected")
    integrations.remove_connection(provider_id)
    return {"provider_id": provider_id, "connected": bool(integrations.get_connection(provider_id))}


@router.post("/{session_id}/documents/{action_id}/export")
async def export_document(session_id: uuid.UUID, action_id: uuid.UUID, payload: ExportRequest):
    """Export a generated document to a connected storage provider.
    Reads the already-generated ActionResult text from storage — the
    export payload is the artifact, never the raw transcript."""
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")

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
        result.result.setdefault("exports", [])
        export_record = {"provider": payload.provider, "url": export.get("url")}
        result.result["exports"].append(export_record)
        storage.upsert_action_results(session_id, [result])
        return {"ok": True, "url": export.get("url"), "provider": payload.provider}

    raise HTTPException(status_code=400, detail=export.get("error") or "Export failed")
