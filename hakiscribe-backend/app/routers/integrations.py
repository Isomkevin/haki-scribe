"""
Connectors API — list, connect (verify), disconnect, and export documents
to connected storage providers. Omi Miniapp auth / setup-completed live here.
"""

import os
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.models.schemas import ActionResult
from app.services import integrations, oauth, omi_pairing, storage

router = APIRouter()


class ConnectRequest(BaseModel):
    credentials: dict[str, Any]


class ExportRequest(BaseModel):
    provider: str  # "google_drive" | "dropbox" | "onedrive"


@router.get("", response_model=list[dict[str, Any]])
def list_integrations():
    return integrations.list_connections()


@router.get("/health")
async def integrations_health():
    return await integrations.check_all_health()


@router.post("/{provider_id}/check")
async def check_integration(provider_id: str):
    if integrations.provider_def(provider_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")
    return await integrations.check_health(provider_id)


def _friendly_oauth(provider_name: str, raw: str) -> tuple[str, str, str]:
    """(reason, title, guidance) for a failed sign-in."""
    text = (raw or "").lower()
    if "access_denied" in text or "cancel" in text or "denied" in text:
        return ("cancelled", f"{provider_name} sign-in cancelled",
                f"You cancelled the {provider_name} sign-in. Nothing was changed — start again whenever you're ready.")
    if "state" in text and ("expired" in text or "invalid" in text or "unknown" in text):
        return ("state_expired", "This sign-in link expired",
                "The sign-in took too long or was opened twice. Close this window and press Sign in again.")
    if "redirect_uri" in text:
        return ("redirect_mismatch", "Sign-in address not approved",
                f"The {provider_name} app doesn't list HakiScribe's callback address. Ask your administrator to add it (see the setup guide).")
    if "invalid_client" in text or "unauthorized_client" in text:
        return ("invalid_client", f"{provider_name} app credentials rejected",
                f"The server's {provider_name} client ID or secret is wrong. Ask your administrator to check them on Render.")
    if "not configured" in text or "not set" in text or "missing" in text and "client" in text:
        return ("not_configured", f"{provider_name} sign-in isn't set up yet",
                f"{provider_name} sign-in isn't switched on on the server yet. Ask your administrator to add it, or paste a token instead.")
    if "invalid_grant" in text or "refresh" in text:
        return ("expired", f"{provider_name} access expired",
                f"Your {provider_name} access has expired or was revoked. Sign in again to reconnect.")
    return ("failed", f"{provider_name} sign-in failed",
            f"{provider_name} didn't complete the sign-in. Try again; if it keeps failing, share this message with your administrator: {raw[:200]}")


def _oauth_fail(provider_id: str, raw: str, status_code: int = 400) -> HTMLResponse:
    definition = integrations.provider_def(provider_id) or {"name": provider_id}
    reason, title, body = _friendly_oauth(str(definition["name"]), raw)
    return HTMLResponse(
        status_code=status_code,
        content=_oauth_html(title=title, body=body, ok=False, provider_id=provider_id, reason=reason),
    )


@router.get("/omi/status")
def omi_status():
    return omi_pairing.status_payload()


# ---------------------------------------------------------------------------
# OAuth — Google Drive, Google Calendar, Dropbox, Microsoft OneDrive
# ---------------------------------------------------------------------------


@router.get("/oauth/{provider_id}/start")
def oauth_start(
    provider_id: str,
    project_id: str | None = Query(default=None),
    location: str | None = Query(default=None),
):
    """Popup lands here; we bounce it to the provider's consent screen.

    Extras such as the Google Cloud project id are stashed with the CSRF
    state and reattached to the credentials after the code exchange."""
    extras = {
        key: value.strip()
        for key, value in (("project_id", project_id or ""), ("location", location or ""))
        if value and value.strip()
    }
    try:
        url = oauth.authorization_url(provider_id, extras or None)
    except oauth.OAuthError as exc:
        return _oauth_fail(provider_id, exc.message, exc.status_code)
    return RedirectResponse(url, status_code=302)


@router.get("/oauth/{provider_id}/callback", response_class=HTMLResponse)
async def oauth_callback(
    provider_id: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    definition = integrations.provider_def(provider_id)
    if definition is None:
        return HTMLResponse(
            status_code=404,
            content=_oauth_html(title="Unknown connector", body=f"No connector called {provider_id}.", ok=False, provider_id=provider_id),
        )
    if error:
        return _oauth_fail(provider_id, f"{error} {error_description or ''}")
    if not code or not state:
        return HTMLResponse(
            status_code=400,
            content=_oauth_html(
                title="Incomplete sign-in",
                body="The provider did not return an authorisation code. Start the connection again.",
                ok=False,
                provider_id=provider_id,
            ),
        )
    try:
        creds = await oauth.exchange_code(provider_id, code, state)
    except oauth.OAuthError as exc:
        return _oauth_fail(provider_id, exc.message, exc.status_code)

    check = await integrations.verify(provider_id, creds)
    if not check["ok"]:
        return _oauth_fail(provider_id, check.get("error") or "The provider rejected the new token.")

    integrations.save_connection(provider_id, creds)
    account = creds.get("account")
    return HTMLResponse(
        content=_oauth_html(
            title=f"{definition['name']} connected",
            body=(f"Signed in as {account}. " if account else "") + "You can close this window.",
            ok=True,
            provider_id=provider_id,
        )
    )


def _oauth_html(*, title: str, body: str, ok: bool, provider_id: str, reason: str = "") -> str:
    import html as _html
    import json as _json

    accent = "#1f4d3a" if ok else "#8b2e2e"
    status = "connected" if ok else "failed"
    msg_js = _json.dumps(body).replace("</", "<\\/")
    reason_js = _json.dumps(reason)
    title = _html.escape(title)
    body = _html.escape(body)
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
    h1 {{ font-size: 1.4rem; margin: 0 0 0.75rem; color: {accent}; }}
    p {{ margin: 0; line-height: 1.55; color: #444; font-family: system-ui, sans-serif; font-size: 0.95rem; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{body}</p>
  </main>
  <script>
    try {{
      if (window.opener) {{
        window.opener.postMessage(
          {{ source: "hakiscribe-oauth", provider: "{provider_id}", status: "{status}", reason: {reason_js}, message: {msg_js} }},
          "*"
        );
      }}
    }} catch (err) {{}}
    setTimeout(function () {{ window.close(); }}, {1200 if ok else 9000});
  </script>
</body>
</html>"""


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
    if provider_id in {"anthropic", "openai", "gemini", "mistral", "openrouter", "intron", "groq"} and not creds.get("api_key"):
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

    payload_data = result.result if isinstance(result.result, dict) else {}

    def _reauth(err: str | None) -> None:
        if integrations.reauth_required(payload.provider) or "401" in (err or "") or "expired" in (err or "").lower():
            name = (integrations.provider_def(payload.provider) or {}).get("name", payload.provider)
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "reauth_required",
                    "provider": payload.provider,
                    "message": f"Your {name} access has expired. Sign in again on the Connectors page to keep exporting.",
                },
            )

    if payload_data.get("start") and payload.provider == "google_calendar":
        event = await integrations.create_calendar_event(
            payload.provider,
            title=str(payload_data.get("title") or result.type.value),
            start=str(payload_data.get("start")),
            end=str(payload_data.get("end") or payload_data.get("start")),
            description=str(payload_data.get("description") or ""),
        )
        if not event["ok"]:
            _reauth(event.get("error"))
            raise HTTPException(status_code=400, detail=event.get("error") or "Could not add the calendar event")
        payload_data.setdefault("exports", [])
        payload_data["exports"].append({"provider": payload.provider, "url": event.get("url")})
        storage.upsert_action_results(session_id, [result])
        return {"ok": True, "url": event.get("url"), "provider": payload.provider}

    text = payload_data.get("document_text")
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

    _reauth(export.get("error"))
    raise HTTPException(status_code=400, detail=export.get("error") or "Export failed")
