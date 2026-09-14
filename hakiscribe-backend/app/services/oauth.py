"""
OAuth 2.0 flows for the storage connectors (Google Drive, Google Calendar,
Dropbox, Microsoft OneDrive).

The browser never sees a client secret or a token: it opens a popup at
``/integrations/oauth/{provider}/start``, the provider redirects back to
``/integrations/oauth/{provider}/callback``, and this module exchanges the
code for tokens server-side and saves them through ``integrations``.

Access tokens are refreshed automatically before each provider call when a
refresh token is present.
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

_CONFIG: dict[str, dict[str, Any]] = {
    "google_drive": {
        "label": "Google Drive",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/drive.file",
            "openid",
            "email",
        ],
        "client_id_env": ("GOOGLE_OAUTH_CLIENT_ID",),
        "client_secret_env": ("GOOGLE_OAUTH_CLIENT_SECRET",),
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "console": "https://console.cloud.google.com/apis/credentials",
    },
    "google_calendar": {
        "label": "Google Calendar",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/calendar.events",
            "openid",
            "email",
        ],
        "client_id_env": ("GOOGLE_OAUTH_CLIENT_ID",),
        "client_secret_env": ("GOOGLE_OAUTH_CLIENT_SECRET",),
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "console": "https://console.cloud.google.com/apis/credentials",
    },
    "gemini_oauth": {
        "label": "Google Gemini (sign in)",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/cloud-platform",
            "openid",
            "email",
        ],
        "client_id_env": ("GOOGLE_OAUTH_CLIENT_ID",),
        "client_secret_env": ("GOOGLE_OAUTH_CLIENT_SECRET",),
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "console": "https://console.cloud.google.com/apis/credentials",
    },
    "dropbox": {
        "label": "Dropbox",
        "authorize_url": "https://www.dropbox.com/oauth2/authorize",
        "token_url": "https://api.dropboxapi.com/oauth2/token",
        "scopes": ["files.content.write", "files.content.read", "account_info.read"],
        "client_id_env": ("DROPBOX_APP_KEY", "DROPBOX_CLIENT_ID"),
        "client_secret_env": ("DROPBOX_APP_SECRET", "DROPBOX_CLIENT_SECRET"),
        "extra_auth_params": {"token_access_type": "offline"},
        "console": "https://www.dropbox.com/developers/apps",
    },
    "onedrive": {
        "label": "Microsoft OneDrive",
        "authorize_url": None,  # tenant-dependent, built below
        "token_url": None,
        "scopes": ["offline_access", "Files.ReadWrite", "User.Read"],
        "client_id_env": ("MICROSOFT_CLIENT_ID", "AZURE_CLIENT_ID"),
        "client_secret_env": ("MICROSOFT_CLIENT_SECRET", "AZURE_CLIENT_SECRET"),
        "extra_auth_params": {},
        "console": "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps",
    },
}


def _env_first(names: tuple[str, ...]) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def _tenant() -> str:
    return (os.environ.get("MICROSOFT_TENANT_ID") or "common").strip() or "common"


def _endpoints(provider_id: str) -> tuple[str, str]:
    cfg = _CONFIG[provider_id]
    if provider_id == "onedrive":
        base = f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0"
        return f"{base}/authorize", f"{base}/token"
    return str(cfg["authorize_url"]), str(cfg["token_url"])


def supports_oauth(provider_id: str) -> bool:
    return provider_id in _CONFIG


def is_configured(provider_id: str) -> bool:
    cfg = _CONFIG.get(provider_id)
    if not cfg:
        return False
    return bool(_env_first(cfg["client_id_env"]) and _env_first(cfg["client_secret_env"]))


def setup_hint(provider_id: str) -> Optional[dict[str, str]]:
    cfg = _CONFIG.get(provider_id)
    if not cfg:
        return None
    return {
        "console": str(cfg["console"]),
        "redirect_uri": redirect_uri(provider_id),
        "client_id_env": cfg["client_id_env"][0],
        "client_secret_env": cfg["client_secret_env"][0],
    }


def public_base_url() -> str:
    base = (
        os.environ.get("OAUTH_REDIRECT_BASE_URL")
        or os.environ.get("BACKEND_INTERNAL_URL")
        or os.environ.get("PUBLIC_BASE_URL")
        or "http://127.0.0.1:8000"
    )
    return base.rstrip("/")


def redirect_uri(provider_id: str) -> str:
    return f"{public_base_url()}/integrations/oauth/{provider_id}/callback"


# ---------------------------------------------------------------------------
# Short-lived state store (CSRF protection for the round trip)
# ---------------------------------------------------------------------------

_STATES: dict[str, dict[str, Any]] = {}
_STATE_TTL_S = 900


def _prune_states() -> None:
    now = time.time()
    for key in [k for k, v in _STATES.items() if now - v["created_at"] > _STATE_TTL_S]:
        _STATES.pop(key, None)


def _issue_state(provider_id: str, extras: Optional[dict[str, str]] = None) -> str:
    _prune_states()
    state = secrets.token_urlsafe(24)
    _STATES[state] = {
        "provider_id": provider_id,
        "created_at": time.time(),
        "extras": dict(extras or {}),
    }
    return state


def _consume_state(state: str, provider_id: str) -> dict[str, str]:
    """Returns the extras stashed when the sign-in started (e.g. project id)."""
    _prune_states()
    entry = _STATES.pop(state, None)
    if entry is None or entry["provider_id"] != provider_id:
        raise OAuthError("This sign-in link has expired. Start the connection again.", 400)
    return dict(entry.get("extras") or {})


# ---------------------------------------------------------------------------
# Authorisation URL
# ---------------------------------------------------------------------------

def authorization_url(provider_id: str, extras: Optional[dict[str, str]] = None) -> str:
    cfg = _CONFIG.get(provider_id)
    if cfg is None:
        raise OAuthError(f"{provider_id} does not use OAuth", 404)
    client_id = _env_first(cfg["client_id_env"])
    if not client_id or not _env_first(cfg["client_secret_env"]):
        raise OAuthError(
            f"{cfg['label']} sign-in is not configured on this server. "
            f"Set {cfg['client_id_env'][0]} and {cfg['client_secret_env'][0]}.",
            503,
        )

    authorize_url, _ = _endpoints(provider_id)
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider_id),
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "state": _issue_state(provider_id, extras),
    }
    params.update({k: str(v) for k, v in cfg["extra_auth_params"].items()})

    from urllib.parse import urlencode

    return f"{authorize_url}?{urlencode(params)}"


# ---------------------------------------------------------------------------
# Code exchange + refresh
# ---------------------------------------------------------------------------

async def _token_request(provider_id: str, form: dict[str, str]) -> dict[str, Any]:
    cfg = _CONFIG[provider_id]
    _, token_url = _endpoints(provider_id)
    form = {
        **form,
        "client_id": _env_first(cfg["client_id_env"]),
        "client_secret": _env_first(cfg["client_secret_env"]),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(token_url, data=form)
    if resp.status_code >= 400:
        raise OAuthError(f"{cfg['label']} rejected the sign-in ({resp.status_code}): {resp.text[:300]}", 400)
    try:
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        raise OAuthError(f"{cfg['label']} returned an unreadable token response: {exc}", 502) from exc


def _creds_from_token(payload: dict[str, Any], previous: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise OAuthError("The provider did not return an access token.", 502)
    expires_in = payload.get("expires_in")
    creds: dict[str, Any] = {
        "access_token": access_token,
        "auth": "oauth",
    }
    refresh = payload.get("refresh_token") or (previous or {}).get("refresh_token")
    if refresh:
        creds["refresh_token"] = str(refresh)
    if isinstance(expires_in, (int, float)):
        creds["expires_at"] = str(int(time.time() + float(expires_in) - 60))
    if previous and previous.get("account"):
        creds["account"] = previous["account"]
    for carried in ("project_id", "location"):
        if previous and previous.get(carried):
            creds[carried] = previous[carried]
    return creds


async def exchange_code(provider_id: str, code: str, state: str) -> dict[str, Any]:
    if provider_id not in _CONFIG:
        raise OAuthError(f"{provider_id} does not use OAuth", 404)
    extras = _consume_state(state, provider_id)
    payload = await _token_request(
        provider_id,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(provider_id),
        },
    )
    creds = _creds_from_token(payload)
    for key, value in extras.items():
        if value:
            creds[key] = value
    account = await _account_label(provider_id, creds["access_token"])
    if account:
        creds["account"] = account
    return creds


async def refresh_if_needed(provider_id: str, creds: dict[str, Any]) -> dict[str, Any]:
    """Return creds with a live access token, refreshing when expired."""
    if provider_id not in _CONFIG:
        return creds
    refresh_token = creds.get("refresh_token")
    expires_at = creds.get("expires_at")
    if not refresh_token:
        return creds
    try:
        expired = expires_at is not None and time.time() >= float(expires_at)
    except (TypeError, ValueError):
        expired = True
    if not expired:
        return creds

    payload = await _token_request(
        provider_id,
        {"grant_type": "refresh_token", "refresh_token": str(refresh_token)},
    )
    fresh = _creds_from_token(payload, previous=creds)
    from app.services import integrations

    integrations.save_connection(provider_id, fresh)
    return fresh


async def _account_label(provider_id: str, access_token: str) -> Optional[str]:
    """Best-effort human label for the connected account — shown on the card."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if provider_id == "gemini_oauth":
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code < 400:
                    data = resp.json()
                    return data.get("email") or data.get("name")
            elif provider_id in {"google_drive", "google_calendar"}:
                resp = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code < 400:
                    user = resp.json().get("user") or {}
                    return user.get("emailAddress") or user.get("displayName")
            elif provider_id == "dropbox":
                resp = await client.post(
                    "https://api.dropboxapi.com/2/users/get_current_account",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code < 400:
                    data = resp.json()
                    return (data.get("email") or (data.get("name") or {}).get("display_name"))
            elif provider_id == "onedrive":
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code < 400:
                    data = resp.json()
                    return data.get("userPrincipalName") or data.get("displayName")
    except Exception as exc:  # noqa: BLE001
        logger.info("Could not read %s account label: %s", provider_id, exc)
    return None
