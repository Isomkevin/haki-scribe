"""
Thin client for HakiChain's hakiscribe-ingress edge function.

Mirrors Ambiguous AI: every call no-ops (returns None) when the HakiChain
connector is not linked, so generation stays usable without HakiChain.
"""

from __future__ import annotations

import contextvars
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_last_error_var: "contextvars.ContextVar[Optional[str]]" = contextvars.ContextVar(
    "hakichain_last_error", default=None
)


def configured() -> bool:
    return bool(_api_key() and _api_base() and _anon_key())


def last_error() -> str | None:
    return _last_error_var.get()


def workspace_url(client_id: str | None) -> str | None:
    if not client_id:
        return None
    origin = (os.environ.get("HAKICHAIN_APP_ORIGIN") or "https://hakichain.com").rstrip("/")
    return f"{origin}/workspace?ws={client_id}"


def _api_key() -> Optional[str]:
    try:
        from app.services import integrations as integrations_service

        creds = integrations_service.get_creds("hakichain")
        if creds and creds.get("api_key"):
            return str(creds["api_key"]).strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _api_base() -> Optional[str]:
    try:
        from app.services import integrations as integrations_service

        creds = integrations_service.get_creds("hakichain")
        base = (creds or {}).get("base_url") if creds else None
        if base and str(base).strip():
            return str(base).strip().rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    env = (os.environ.get("HAKICHAIN_API_BASE") or "").strip().rstrip("/")
    return env or None


def _anon_key() -> Optional[str]:
    return (os.environ.get("HAKICHAIN_SUPABASE_ANON_KEY") or "").strip() or None


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "apikey": _anon_key() or "",
        "Content-Type": "application/json",
    }


def _set_error(message: str) -> None:
    _last_error_var.set(message)
    logger.warning("HakiChain %s; keeping local result", message)


async def _request(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not configured():
        return None
    _last_error_var.set(None)
    base = _api_base()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(base, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                _set_error(f"{payload.get('action')} -> {resp.status_code}: {resp.text[:240]}")
                return None
            if not resp.content:
                return {}
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                _set_error(str(data["error"]))
                return None
            return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        _set_error(f"{payload.get('action')} failed ({exc})")
        return None


async def me(api_key: str, base_url: str | None = None) -> dict[str, Any]:
    """Live verify used by the Connectors page. Does not require a saved connection."""
    base = (base_url or "").strip().rstrip("/") or _api_base()
    anon = _anon_key()
    if not base:
        return {"ok": False, "error": "HAKICHAIN_API_BASE is not set on the server (or paste a base URL)."}
    if not anon:
        return {"ok": False, "error": "HAKICHAIN_SUPABASE_ANON_KEY is not set on the server."}
    if not api_key or not api_key.startswith("hkc_"):
        return {"ok": False, "error": "Paste a HakiChain token that starts with hkc_"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                base,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "apikey": anon,
                    "Content-Type": "application/json",
                },
                json={"action": "me"},
            )
            if resp.status_code >= 400:
                return {"ok": False, "error": f"HakiChain returned {resp.status_code}: {resp.text[:200]}"}
            data = resp.json() if resp.content else {}
            if not isinstance(data, dict) or data.get("error"):
                return {"ok": False, "error": str((data or {}).get("error") or "Unexpected response")}
            account = data.get("account") or data.get("email") or data.get("user_id")
            return {"ok": True, "error": None, "account": account, "user_id": data.get("user_id")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def file_matter(
    *,
    action_key: str,
    scribe_matter_id: str,
    matter_name: str,
    client_name: str,
    session_id: str | None = None,
) -> Optional[dict[str, Any]]:
    return await _request(
        {
            "action": "file_matter",
            "action_key": action_key,
            "scribe_matter_id": scribe_matter_id,
            "session_id": session_id,
            "matter_name": matter_name,
            "client_name": client_name,
        }
    )


async def file_document(
    *,
    action_key: str,
    session_id: str,
    title: str,
    document_text: str,
    client_id: str | None = None,
    matter_name: str | None = None,
    client_name: str | None = None,
) -> Optional[dict[str, Any]]:
    return await _request(
        {
            "action": "file_document",
            "action_key": action_key,
            "session_id": session_id,
            "client_id": client_id,
            "title": title,
            "document_text": document_text,
            "matter_name": matter_name,
            "client_name": client_name,
        }
    )


async def file_reminder(
    *,
    action_key: str,
    session_id: str,
    title: str,
    start: str,
    description: str = "",
    client_id: str | None = None,
    matter_name: str | None = None,
    client_name: str | None = None,
    reminder_type: str | None = None,
) -> Optional[dict[str, Any]]:
    return await _request(
        {
            "action": "file_reminder",
            "action_key": action_key,
            "session_id": session_id,
            "client_id": client_id,
            "title": title,
            "start": start,
            "description": description,
            "matter_name": matter_name,
            "client_name": client_name,
            "reminder_type": reminder_type,
        }
    )
