"""
Integration registry — lets a HakiScribe user link the platform to external
tools (AI assistants, cloud storage, practice suites) so drafted documents,
research and calendar events can flow to where their practice already lives.

Connections are persisted as a new ``haki_records`` kind ``"integrations"``
when ``DATABASE_URL`` is set, and otherwise live in the in-memory store /
JSON snapshot file alongside everything else.

Credentials are stored server-side only. The API never returns a full
credential — only a masked hint (``sk-…9f2``) and a connected-at timestamp.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

# Each provider declares:
#   id           — short slug used in the URL and API
#   name         — display name
#   group        — "ai" | "storage" | "practice"
#   fields       — list of {id, label, type, help, placeholder, mask} dicts
#   what_it_does — one-liner shown on the card
#   verify       — async fn(creds: dict) -> dict[str, Any]  (returns {"ok": bool, "error": str|None})
#   capabilities — list of strings the frontend can show ("Ask an AI model", "Export documents")

_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "anthropic",
        "name": "Anthropic (Claude)",
        "group": "ai",
        "what_it_does": "Run the “Ask an AI model” task through your own Claude key.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "Anthropic API key",
                "type": "password",
                "help": "Found in your Anthropic Console → API Keys.",
                "placeholder": "sk-ant-…",
                "mask": True,
            },
        ],
    },
    {
        "id": "openai",
        "name": "OpenAI (GPT)",
        "group": "ai",
        "what_it_does": "Run the “Ask an AI model” task through your own OpenAI key.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "OpenAI API key",
                "type": "password",
                "help": "Found in platform.openai.com → API Keys.",
                "placeholder": "sk-…",
                "mask": True,
            },
        ],
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "group": "ai",
        "what_it_does": "Run the “Ask an AI model” task through your own Gemini key.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "Google AI Studio key",
                "type": "password",
                "help": "Found in aistudio.google.com → API keys.",
                "placeholder": "AIza…",
                "mask": True,
            },
        ],
    },
    {
        "id": "gemini_oauth",
        "name": "Google Gemini (sign in)",
        "group": "ai",
        "auth": "oauth",
        "what_it_does": "Sign in with Google and run the “Ask an AI model” task on Gemini through Vertex AI.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "project_id",
                "label": "Google Cloud project ID",
                "type": "text",
                "help": "The project where Vertex AI is enabled, e.g. hakiscribe-demo.",
                "placeholder": "my-project-id",
                "mask": False,
            },
            {
                "id": "location",
                "label": "Vertex AI region",
                "type": "text",
                "help": "Leave blank for us-central1.",
                "placeholder": "us-central1",
                "mask": False,
            },
        ],
    },
    {
        "id": "groq",
        "name": "Groq",
        "group": "ai",
        "what_it_does": "Run the “Ask an AI model” task on Groq's very fast Llama models.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "Groq API key",
                "type": "password",
                "help": "Found in console.groq.com → API Keys. The workspace GROQ_API_KEY is used automatically when set.",
                "placeholder": "gsk_…",
                "mask": True,
            },
        ],
    },
    {
        "id": "mistral",
        "name": "Mistral",
        "group": "ai",
        "what_it_does": "Run the “Ask an AI model” task through your own Mistral key.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "Mistral API key",
                "type": "password",
                "help": "Found in console.mistral.ai → API Keys.",
                "placeholder": "…",
                "mask": True,
            },
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "group": "ai",
        "what_it_does": "Route the “Ask an AI model” task through any model OpenRouter serves.",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "api_key",
                "label": "OpenRouter API key",
                "type": "password",
                "help": "Found in openrouter.ai → Keys. The workspace OPENROUTER_API_KEY is used automatically when set.",
                "placeholder": "sk-or-…",
                "mask": True,
            },
            {
                "id": "default_model",
                "label": "Default Ask model",
                "type": "text",
                "help": "OpenRouter model id used by the Ask composer when no model is chosen (ASK_MODEL).",
                "placeholder": "openai/gpt-4o",
                "mask": False,
            },
        ],
    },
    {
        "id": "intron",
        "name": "Intron Sahara (Voice AI)",
        "group": "ai",
        "what_it_does": "Transcribe African code-switched speech with Sahara for multilingual legal sessions.",
        "capabilities": ["Speech-to-text", "Legal court hearing format"],
        "fields": [
            {
                "id": "api_key",
                "label": "Intron API key",
                "type": "password",
                "help": "From voice.intron.io → Developers. Workspace INTRON_API_KEY is used automatically when set.",
                "placeholder": "…",
                "mask": True,
            },
        ],
    },
    {
        "id": "claude_custom",
        "name": "Custom OpenAI-compatible endpoint",
        "group": "ai",
        "what_it_does": "Point HakiScribe at any OpenAI-compatible API (Legora, Harvey, on-prem LLM).",
        "capabilities": ["Ask an AI model"],
        "fields": [
            {
                "id": "base_url",
                "label": "Base URL",
                "type": "text",
                "help": "e.g. https://api.legora.ai/v1 or https://harvey.example.com/v1",
                "placeholder": "https://…/v1",
                "mask": False,
            },
            {
                "id": "api_key",
                "label": "API key",
                "type": "password",
                "help": "The bearer token the endpoint expects.",
                "placeholder": "…",
                "mask": True,
            },
        ],
    },
    {
        "id": "nvidia_nim",
        "name": "NVIDIA NIM",
        "group": "ai",
        "what_it_does": "Run transcription, action detection and drafting on your own NVIDIA NIM GPU service.",
        "capabilities": ["Speech-to-text", "Ask an AI model", "Action detection and drafting"],
        "fields": [
            {
                "id": "llm_endpoint",
                "label": "Language model endpoint",
                "type": "text",
                "help": "Base URL of your NIM chat service, e.g. https://llm.example/v1. Workspace NVIDIA_NIM_LLM_ENDPOINT is used automatically when set.",
                "placeholder": "https://llm.example/v1",
                "mask": False,
            },
            {
                "id": "llm_model",
                "label": "Model name",
                "type": "text",
                "help": "Leave blank for meta/llama-3.1-8b-instruct.",
                "placeholder": "meta/llama-3.1-8b-instruct",
                "mask": False,
            },
            {
                "id": "asr_endpoint",
                "label": "Speech-to-text endpoint",
                "type": "text",
                "help": "Optional. Base URL of your NIM ASR service, e.g. https://asr.example/v1.",
                "placeholder": "https://asr.example/v1",
                "mask": False,
            },
            {
                "id": "api_key",
                "label": "Bearer token",
                "type": "password",
                "help": "Only needed when your NIM container or proxy requires authentication.",
                "placeholder": "…",
                "mask": True,
            },
        ],
    },
    {
        "id": "google_drive",
        "name": "Google Drive",
        "group": "storage",
        "auth": "oauth",
        "what_it_does": "Sign in with Google and send drafted documents to your firm's Drive.",
        "capabilities": ["Export documents"],
        "fields": [
            {
                "id": "access_token",
                "label": "Google Drive access token",
                "type": "password",
                "help": "Optional manual fallback — normally you just sign in with Google.",
                "placeholder": "ya29.…",
                "mask": True,
            },
        ],
    },
    {
        "id": "google_calendar",
        "name": "Google Calendar",
        "group": "storage",
        "auth": "oauth",
        "what_it_does": "Sign in with Google and push court dates and client meetings to your calendar.",
        "capabilities": ["Add calendar events"],
        "fields": [
            {
                "id": "access_token",
                "label": "Google Calendar access token",
                "type": "password",
                "help": "Optional manual fallback — normally you just sign in with Google.",
                "placeholder": "ya29.…",
                "mask": True,
            },
        ],
    },
    {
        "id": "dropbox",
        "name": "Dropbox",
        "group": "storage",
        "auth": "oauth",
        "what_it_does": "Sign in with Dropbox and send drafted documents straight to your folders.",
        "capabilities": ["Export documents"],
        "fields": [
            {
                "id": "access_token",
                "label": "Dropbox access token",
                "type": "password",
                "help": "Optional manual fallback — normally you just sign in with Dropbox.",
                "placeholder": "sl.…",
                "mask": True,
            },
        ],
    },
    {
        "id": "onedrive",
        "name": "Microsoft OneDrive",
        "group": "storage",
        "auth": "oauth",
        "what_it_does": "Sign in with Microsoft and send drafted documents to your OneDrive.",
        "capabilities": ["Export documents"],
        "fields": [
            {
                "id": "access_token",
                "label": "Microsoft Graph access token",
                "type": "password",
                "help": "Optional manual fallback — normally you just sign in with Microsoft.",
                "placeholder": "eyJ…",
                "mask": True,
            },
        ],
    },
    {
        "id": "hakichain",
        "name": "HakiChain",
        "group": "practice",
        "what_it_does": "Sync matters and sessions to your HakiChain workspace.",
        "capabilities": ["Sync matters"],
        "fields": [
            {
                "id": "api_key",
                "label": "HakiChain API token",
                "type": "password",
                "help": "Found in HakiChain → Workspace → API tokens.",
                "placeholder": "hkc_…",
                "mask": True,
            },
        ],
    },
    {
        "id": "ambiguous",
        "name": "Ambiguous AI",
        "group": "practice",
        "what_it_does": "Send drafted documents to Docs, court dates to Calendar, matters/contacts to CRM, and a review ping to Chat.",
        "capabilities": ["Export documents", "Add calendar events", "Sync matters", "Chat notification"],
        "fields": [
            {
                "id": "api_key",
                "label": "Ambiguous AI API key",
                "type": "password",
                "help": "From app.ambiguous.ai → mint a key at /mcp, or Developers → API keys. The workspace AMBIGUOUS_API_KEY is used automatically when set.",
                "placeholder": "ak_…",
                "mask": True,
            },
            {
                "id": "calendar_id",
                "label": "Calendar ID (optional)",
                "type": "text",
                "help": "Where court dates should be created. Leave blank to use the first calendar available to this key. Overrides AMBIGUOUS_CALENDAR_ID.",
                "placeholder": "Calendar UUID",
            },
            {
                "id": "notify_channel",
                "label": "Chat channel ID (optional)",
                "type": "text",
                "help": "Where review-ready notifications should be posted. Use the channel UUID from Ambiguous. Overrides AMBIGUOUS_NOTIFY_CHANNEL.",
                "placeholder": "Channel UUID",
            },
        ],
    },
    {
        "id": "omi",
        "name": "Omi wearable",
        "group": "practice",
        "what_it_does": "Receive live transcripts from the Omi app store integration, and import finished conversations with an Omi developer key.",
        "capabilities": ["Live transcript", "Finished memories", "Import conversations"],
        "fields": [
            {
                "id": "uid",
                "label": "Omi user id",
                "type": "text",
                "help": "Filled automatically when you open the setup link from the Omi app.",
                "placeholder": "omi-user-…",
                "mask": True,
            },
            {
                "id": "api_key",
                "label": "Omi developer API key",
                "type": "password",
                "help": "Omi app → Settings → Developer → Create key.",
                "placeholder": "omi_dev_…",
                "mask": True,
            },
        ],
    },
]


def provider_ids() -> list[str]:
    return [p["id"] for p in _PROVIDERS]


def provider_def(provider_id: str) -> Optional[dict[str, Any]]:
    for p in _PROVIDERS:
        if p["id"] == provider_id:
            return p
    return None


# ---------------------------------------------------------------------------
# Credential masking
# ---------------------------------------------------------------------------

def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return value[:2] + "…"
    return value[:3] + "…" + value[-3:]


def _mask_creds(provider_id: str, creds: dict[str, Any]) -> dict[str, str]:
    definition = provider_def(provider_id)
    if definition is None:
        return {}
    masked: dict[str, str] = {}
    if creds.get("account"):
        masked["account"] = str(creds["account"])
    for field in definition["fields"]:
        raw = str(creds.get(field["id"], ""))
        masked[field["id"]] = _mask(raw) if field.get("mask", True) else raw
    return masked


# ---------------------------------------------------------------------------
# In-memory connection store (persisted via storage snapshot)
# ---------------------------------------------------------------------------

_connections: dict[str, dict[str, Any]] = {}
# provider_id -> {"provider_id", "connected_at", "creds": {...}}

# Workspace .env keys that should appear as connected connectors so the
# Ask composer can route through the same OpenRouter (or OpenAI) config
# used for detection and drafting — without pasting the key in the UI.
_ENV_CREDENTIAL_FIELDS: dict[str, dict[str, str]] = {
    "openrouter": {"api_key": "OPENROUTER_API_KEY", "default_model": "ASK_MODEL"},
    "openai": {"api_key": "OPENAI_API_KEY"},
    "intron": {"api_key": "INTRON_API_KEY"},
    "groq": {"api_key": "GROQ_API_KEY"},
    "nvidia_nim": {
        "llm_endpoint": "NVIDIA_NIM_LLM_ENDPOINT",
        "asr_endpoint": "NVIDIA_NIM_ASR_ENDPOINT",
        "llm_model": "NVIDIA_NIM_LLM_MODEL",
        "api_key": "NVIDIA_NIM_API_KEY",
    },
    "ambiguous": {
        "api_key": "AMBIGUOUS_API_KEY",
        "calendar_id": "AMBIGUOUS_CALENDAR_ID",
        "notify_channel": "AMBIGUOUS_NOTIFY_CHANNEL",
    },
}


def _env_creds(provider_id: str) -> Optional[dict[str, str]]:
    mapping = _ENV_CREDENTIAL_FIELDS.get(provider_id)
    if not mapping:
        return None
    creds: dict[str, str] = {}
    for field_id, env_name in mapping.items():
        value = os.environ.get(env_name, "").strip()
        if value:
            creds[field_id] = value
    if provider_id == "openrouter" and not creds.get("api_key"):
        return None
    if provider_id == "openai" and not creds.get("api_key"):
        return None
    if provider_id in {"intron", "groq", "ambiguous"} and not creds.get("api_key"):
        return None
    if provider_id == "nvidia_nim" and not (creds.get("llm_endpoint") or creds.get("asr_endpoint")):
        return None
    return creds or None


def _provider_meta(provider: dict[str, Any]) -> dict[str, Any]:
    from app.services import oauth

    pid = provider["id"]
    uses_oauth = provider.get("auth") == "oauth" and oauth.supports_oauth(pid)
    return {
        "provider_id": pid,
        "name": provider["name"],
        "group": provider["group"],
        "what_it_does": provider["what_it_does"],
        "capabilities": provider["capabilities"],
        "fields": provider["fields"],
        "auth": "oauth" if uses_oauth else "api_key",
        "oauth": uses_oauth,
        "oauth_configured": uses_oauth and oauth.is_configured(pid),
        "oauth_setup": oauth.setup_hint(pid) if uses_oauth else None,
    }


def list_connections() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for provider in _PROVIDERS:
        pid = provider["id"]
        conn = get_connection(pid)
        if conn:
            result.append(
                {
                    **_provider_meta(provider),
                    "connected": True,
                    "connected_at": conn.get("connected_at"),
                    "source": conn.get("source") or "user",
                    "account": (conn.get("creds") or {}).get("account"),
                    "masked_creds": _mask_creds(pid, conn.get("creds", {})),
                    **_health_fields(pid),
                }
            )
        else:
            result.append(
                {
                    **_provider_meta(provider),
                    "connected": False,
                    "connected_at": None,
                    "source": None,
                    "account": None,
                    "masked_creds": {},
                    "health": "not_connected",
                    "health_error": None,
                    "last_checked_at": None,
                }
            )
    return result


def get_connection(provider_id: str) -> Optional[dict[str, Any]]:
    saved = _connections.get(provider_id)
    if saved:
        return {**saved, "source": "user"}
    env = _env_creds(provider_id)
    if env:
        return {
            "provider_id": provider_id,
            "connected_at": None,
            "creds": env,
            "source": "workspace",
        }
    return None


def get_creds(provider_id: str) -> Optional[dict[str, Any]]:
    conn = get_connection(provider_id)
    return conn.get("creds") if conn else None


_refresh_errors: dict[str, str] = {}
_health: dict[str, dict[str, Any]] = {}


def _health_fields(provider_id: str) -> dict[str, Any]:
    h = _health.get(provider_id) or {}
    return {
        "health": h.get("health") or "unchecked",
        "health_error": h.get("error"),
        "last_checked_at": h.get("checked_at"),
    }


def reauth_required(provider_id: str) -> bool:
    return provider_id in _refresh_errors or (_health.get(provider_id) or {}).get("health") == "expired"


def _classify(provider_id: str, error: str) -> str:
    text = (error or "").lower()
    if provider_id in _refresh_errors or "invalid_grant" in text or "expired" in text or "refresh" in text:
        return "expired"
    if any(k in text for k in ("timeout", "timed out", "connecterror", "returned 5", "unreachable", "name or service")):
        return "unreachable"
    return "invalid"


def _friendly_health_error(provider_id: str, health: str, raw: str) -> str:
    name = (provider_def(provider_id) or {}).get("name", provider_id)
    if health == "expired":
        return f"Your {name} access has expired. Sign in again to keep using it."
    if health == "unreachable":
        return f"{name} could not be reached just now. Try again in a minute."
    if "401" in raw or "403" in raw:
        return f"{name} rejected the saved key. Paste a new key or reconnect. ({raw[:160]})"
    return raw[:240] or f"{name} did not accept the saved credentials."


async def check_health(provider_id: str) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    if get_connection(provider_id) is None:
        _health.pop(provider_id, None)
        return {"provider_id": provider_id, "health": "not_connected", "health_error": None, "last_checked_at": now}
    _refresh_errors.pop(provider_id, None)
    try:
        creds = await asyncio.wait_for(get_fresh_creds(provider_id), timeout=20)
        result = await asyncio.wait_for(verify(provider_id, creds or {}), timeout=20)
    except asyncio.TimeoutError:
        result = {"ok": False, "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "error": str(exc)}
    if result.get("ok"):
        health, err = "valid", None
    else:
        raw = str(result.get("error") or "")
        health = _classify(provider_id, raw)
        err = _friendly_health_error(provider_id, health, raw)
    _health[provider_id] = {"health": health, "error": err, "checked_at": now}
    return {"provider_id": provider_id, "health": health, "health_error": err, "last_checked_at": now}


async def check_all_health() -> list[dict[str, Any]]:
    return list(await asyncio.gather(*(check_health(p["id"]) for p in _PROVIDERS)))


async def get_fresh_creds(provider_id: str) -> Optional[dict[str, Any]]:
    """Creds with a live access token — refreshes OAuth tokens when expired."""
    creds = get_creds(provider_id)
    if creds is None:
        return None
    from app.services import oauth

    if not oauth.supports_oauth(provider_id):
        return creds
    try:
        return await oauth.refresh_if_needed(provider_id, creds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not refresh %s token: %s", provider_id, exc)
        _refresh_errors[provider_id] = str(getattr(exc, "message", None) or exc)
        return creds


def save_connection(provider_id: str, creds: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    _connections[provider_id] = {
        "provider_id": provider_id,
        "connected_at": now,
        "creds": creds,
    }
    _persist_integrations()
    return _connections[provider_id]


def remove_connection(provider_id: str) -> bool:
    if provider_id in _connections:
        del _connections[provider_id]
        _persist_integrations()
        return True
    return False


def can_disconnect(provider_id: str) -> bool:
    """Workspace env keys stay connected until the env var is removed."""
    return provider_id in _connections


def connections_snapshot() -> list[dict[str, Any]]:
    """Serialise for persistence — creds included (server-side store only)."""
    return list(_connections.values())


def restore_connections(payload: list[dict[str, Any]]) -> None:
    _connections.clear()
    for item in payload:
        pid = item.get("provider_id")
        if pid and provider_def(pid):
            _connections[pid] = item


# ---------------------------------------------------------------------------
# Persistence — piggybacks on the existing storage snapshot
# ---------------------------------------------------------------------------

def _persist_integrations() -> None:
    """Ask storage to save the full snapshot so integrations survive restarts."""
    try:
        from app.services import storage
        storage._persist()  # noqa: SLF001 — internal, same module family
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not persist integrations: %s", exc)


# ---------------------------------------------------------------------------
# Verification — real API calls that confirm the credential works
# ---------------------------------------------------------------------------

async def _verify_anthropic(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Anthropic returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_groq(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Groq returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_openai(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"OpenAI returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_gemini(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=1",
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Gemini returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_mistral(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Mistral returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_openrouter(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"OpenRouter returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _nim_base(value: Any) -> str:
    base = str(value or "").strip().rstrip("/")
    if not base:
        return ""
    for suffix in ("/chat/completions", "/audio/transcriptions"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base.rstrip("/")


async def _verify_nvidia_nim(creds: dict[str, Any]) -> dict[str, Any]:
    llm = _nim_base(creds.get("llm_endpoint"))
    asr = _nim_base(creds.get("asr_endpoint"))
    if not llm and not asr:
        return {"ok": False, "error": "Add at least one NVIDIA NIM endpoint URL."}
    key = str(creds.get("api_key") or "").strip()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    errors: list[str] = []
    for label, base in (("Language model", llm), ("Speech-to-text", asr)):
        if not base:
            continue
        url = base if base.endswith("/v1") else f"{base}/v1"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(f"{url}/models", headers=headers)
            if resp.status_code >= 400:
                errors.append(f"{label} endpoint returned {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label} endpoint could not be reached: {exc}")
    if errors:
        return {"ok": False, "error": " ".join(errors)}
    return {"ok": True, "error": None}



def _tiny_silent_wav() -> bytes:
    """Minimal WAV used only to probe whether an Intron API key is accepted."""
    import struct

    sample_rate = 16000
    duration_samples = 1600  # 0.1s
    data_size = duration_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + (b"\x00\x00" * duration_samples)


async def _verify_intron(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://infer.voice.intron.io/file/v1/upload/sync",
                headers={"Authorization": f"Bearer {key}"},
                files={
                    "audio_file_blob": ("probe.wav", _tiny_silent_wav(), "audio/wav"),
                },
                data={
                    "audio_file_name": "hakiscribe-probe.wav",
                    "use_language_asr_input": "en",
                },
            )
            if resp.status_code in (401, 403):
                return {"ok": False, "error": "Intron rejected the API key"}
            if resp.status_code >= 500 and resp.status_code != 503:
                return {"ok": False, "error": f"Intron unavailable ({resp.status_code})"}
            # 200 / 400 (bad audio) / 503 (queued) all mean the key was accepted.
            return {"ok": True, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_custom_openai(creds: dict[str, Any]) -> dict[str, Any]:
    base = (creds.get("base_url") or "").strip().rstrip("/")
    key = creds.get("api_key", "")
    if not base:
        return {"ok": False, "error": "Missing base URL"}
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{base}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Endpoint returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_google_drive(creds: dict[str, Any]) -> dict[str, Any]:
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "Missing access token"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/drive/v3/about?fields=user",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Google Drive returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_dropbox(creds: dict[str, Any]) -> dict[str, Any]:
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "Missing access token"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.dropboxapi.com/2/users/get_current_account",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Dropbox returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_onedrive(creds: dict[str, Any]) -> dict[str, Any]:
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "Missing access token"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me/drive",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"OneDrive returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


async def _verify_hakichain(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API token"}
    # HakiChain API endpoint — we accept the token and confirm it's non-empty.
    # The real HakiChain API will be wired once the endpoint is published.
    return {"ok": True, "error": None}


async def _verify_ambiguous(creds: dict[str, Any]) -> dict[str, Any]:
    key = creds.get("api_key", "")
    if not key:
        return {"ok": False, "error": "Missing API key"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://app.ambiguous.ai/api/documents",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Ambiguous AI returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


OMI_API_BASE = os.environ.get("OMI_API_BASE", "https://api.omi.me/v1/dev")


async def _verify_omi(creds: dict[str, Any]) -> dict[str, Any]:
    """Valid when the app-store link has a uid and/or the developer key is
    accepted by Omi's API. A key that Omi rejects is reported as invalid."""
    uid = str(creds.get("uid") or "").strip()
    key = str(creds.get("api_key") or "").strip()
    if not uid and not key:
        return {"ok": False, "error": "Link Omi from the Omi app, or paste an Omi developer API key."}
    if key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{OMI_API_BASE}/user/conversations",
                    params={"limit": 1},
                    headers={"Authorization": f"Bearer {key}"},
                )
            if resp.status_code in (401, 403):
                return {"ok": False, "error": "Omi rejected the developer API key. Create a new one in the Omi app."}
            if resp.status_code >= 400:
                return {"ok": False, "error": f"Omi returned {resp.status_code}: {resp.text[:160]}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"Could not reach Omi: {exc}"}
    return {"ok": True, "error": None}


async def _verify_google_calendar(creds: dict[str, Any]) -> dict[str, Any]:
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "Missing access token"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Google Calendar returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def vertex_location(creds: dict[str, Any]) -> str:
    return (str(creds.get("location") or "").strip() or os.environ.get("VERTEX_LOCATION") or "us-central1")


async def _verify_gemini_oauth(creds: dict[str, Any]) -> dict[str, Any]:
    token = creds.get("access_token", "")
    project = str(creds.get("project_id") or "").strip()
    if not token:
        return {"ok": False, "error": "Sign in with Google first"}
    if not project:
        return {"ok": False, "error": "Missing Google Cloud project ID"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code < 400:
                return {"ok": True, "error": None}
            return {
                "ok": False,
                "error": (
                    f"Google could not open project “{project}” ({resp.status_code}). "
                    "Check the project ID and that this account has access."
                ),
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


_VERIFIERS = {
    "gemini_oauth": _verify_gemini_oauth,
    "google_calendar": _verify_google_calendar,
    "anthropic": _verify_anthropic,
    "openai": _verify_openai,
    "gemini": _verify_gemini,
    "mistral": _verify_mistral,
    "groq": _verify_groq,
    "openrouter": _verify_openrouter,
    "nvidia_nim": _verify_nvidia_nim,
    "intron": _verify_intron,
    "claude_custom": _verify_custom_openai,
    "google_drive": _verify_google_drive,
    "dropbox": _verify_dropbox,
    "onedrive": _verify_onedrive,
    "hakichain": _verify_hakichain,
    "ambiguous": _verify_ambiguous,
    "omi": _verify_omi,
}


async def verify(provider_id: str, creds: dict[str, Any]) -> dict[str, Any]:
    verifier = _VERIFIERS.get(provider_id)
    if verifier is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}
    return await verifier(creds)


# ---------------------------------------------------------------------------
# Document export — storage providers receive the generated artifact
# ---------------------------------------------------------------------------

async def export_document(provider_id: str, text: str, title: str) -> dict[str, Any]:
    """Upload a drafted document to the connected storage provider.
    Returns {"ok": bool, "url": str|None, "error": str|None}."""
    creds = await get_fresh_creds(provider_id)
    if creds is None:
        return {"ok": False, "url": None, "error": "Provider not connected"}

    if provider_id == "google_drive":
        return await _export_google_drive(creds, text, title)
    elif provider_id == "dropbox":
        return await _export_dropbox(creds, text, title)
    elif provider_id == "onedrive":
        return await _export_onedrive(creds, text, title)
    return {"ok": False, "url": None, "error": f"Provider {provider_id} does not support document export"}


async def _export_google_drive(creds: dict[str, Any], text: str, title: str) -> dict[str, Any]:
    token = creds.get("access_token", "")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Upload metadata + content in a multipart/related request
            import json
            boundary = "hakiscribe-boundary"
            metadata = json.dumps({"name": f"{title}.txt", "mimeType": "text/plain"})
            body = (
                f"--{boundary}\r\n"
                "Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{metadata}\r\n"
                f"--{boundary}\r\n"
                "Content-Type: text/plain\r\n\r\n"
                f"{text}\r\n"
                f"--{boundary}--"
            )
            resp = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                content=body.encode("utf-8"),
            )
            if resp.status_code < 400:
                file_id = resp.json().get("id")
                return {"ok": True, "url": f"https://drive.google.com/file/d/{file_id}/view" if file_id else None, "error": None}
            return {"ok": False, "url": None, "error": f"Google Drive returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": None, "error": str(exc)}


async def _export_dropbox(creds: dict[str, Any], text: str, title: str) -> dict[str, Any]:
    token = creds.get("access_token", "")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Dropbox-API-Arg": f'{{"path": "/HakiScribe/{title}.txt","mode":"add","autorename":true,"mute":false}}',
                    "Content-Type": "application/octet-stream",
                },
                content=text.encode("utf-8"),
            )
            if resp.status_code < 400:
                return {"ok": True, "url": None, "error": None}
            return {"ok": False, "url": None, "error": f"Dropbox returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": None, "error": str(exc)}


async def _export_onedrive(creds: dict[str, Any], text: str, title: str) -> dict[str, Any]:
    token = creds.get("access_token", "")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"https://graph.microsoft.com/v1.0/me/drive/root:/HakiScribe/{title}.txt:/content",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "text/plain",
                },
                content=text.encode("utf-8"),
            )
            if resp.status_code < 400:
                return {"ok": True, "url": None, "error": None}
            return {"ok": False, "url": None, "error": f"OneDrive returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": None, "error": str(exc)}


async def create_calendar_event(
    provider_id: str,
    *,
    title: str,
    start: str,
    end: str,
    description: str = "",
) -> dict[str, Any]:
    """Push a generated calendar event to a connected calendar provider."""
    creds = await get_fresh_creds(provider_id)
    if creds is None:
        return {"ok": False, "url": None, "error": "Provider not connected"}
    if provider_id != "google_calendar":
        return {"ok": False, "url": None, "error": f"Provider {provider_id} does not support calendar events"}

    token = creds.get("access_token", "")
    calendar_id = (os.environ.get("GOOGLE_CALENDAR_ID") or "primary").strip() or "primary"
    body: dict[str, Any] = {
        "summary": title,
        "description": description,
        "start": _gcal_time(start),
        "end": _gcal_time(end or start),
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
            )
            if resp.status_code < 400:
                data = resp.json()
                return {"ok": True, "url": data.get("htmlLink"), "error": None}
            return {"ok": False, "url": None, "error": f"Google Calendar returned {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": None, "error": str(exc)}


def _gcal_time(value: str) -> dict[str, str]:
    raw = (value or "").strip()
    timezone = (os.environ.get("GOOGLE_CALENDAR_TIMEZONE") or "Africa/Nairobi").strip()
    if len(raw) == 10 and raw.count("-") == 2:
        return {"date": raw}
    return {"dateTime": raw, "timeZone": timezone}


# ---------------------------------------------------------------------------
# LLM completion via a connected provider key
# ---------------------------------------------------------------------------

async def complete_with_provider(
    provider_id: str,
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    timeout_s: float = 120.0,
) -> Optional[str]:
    """Run a completion through the user's own connected LLM key.
    Returns None when the provider is not connected or the call fails."""
    creds = await get_fresh_creds(provider_id)
    if creds is None:
        return None
    try:
        if provider_id == "anthropic":
            return await _complete_anthropic(creds, system_prompt, user_prompt, model or "claude-3-5-sonnet-20241022", timeout_s)
        elif provider_id == "openai":
            return await _complete_openai(creds, system_prompt, user_prompt, model or "gpt-4o", timeout_s, "https://api.openai.com/v1")
        elif provider_id == "gemini":
            return await _complete_gemini(creds, system_prompt, user_prompt, model or "gemini-1.5-flash", timeout_s)
        elif provider_id == "mistral":
            return await _complete_openai(creds, system_prompt, user_prompt, model or "mistral-large-latest", timeout_s, "https://api.mistral.ai/v1")
        elif provider_id == "groq":
            return await _complete_openai(creds, system_prompt, user_prompt, model or "llama-3.3-70b-versatile", timeout_s, "https://api.groq.com/openai/v1")
        elif provider_id == "openrouter":
            return await _complete_openai(
                creds,
                system_prompt,
                user_prompt,
                model or creds.get("default_model") or "openai/gpt-4o",
                timeout_s,
                "https://openrouter.ai/api/v1",
                extra_headers=openrouter_headers(),
            )
        elif provider_id == "gemini_oauth":
            return await _complete_vertex_gemini(creds, system_prompt, user_prompt, model or "gemini-2.0-flash", timeout_s)
        elif provider_id == "claude_custom":
            base = (creds.get("base_url") or "").strip().rstrip("/")
            return await _complete_openai(creds, system_prompt, user_prompt, model or "gpt-4o", timeout_s, base)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Provider %s completion failed: %s", provider_id, exc)
        return None


async def _complete_anthropic(creds: dict, system_prompt: str, user_prompt: str, model: str, timeout_s: float) -> Optional[str]:
    key = creds.get("api_key", "")
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        resp.raise_for_status()
        content = resp.json().get("content", [])
        if content and isinstance(content, list):
            return (content[0].get("text") or "").strip() or None
        return None


def openrouter_headers() -> dict[str, str]:
    referer = (
        os.environ.get("OPENROUTER_HTTP_REFERER")
        or os.environ.get("BACKEND_INTERNAL_URL")
        or "https://hakiscribe.lovable.app"
    )
    return {
        "HTTP-Referer": referer.rstrip("/"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE") or "HakiScribe",
    }


async def _complete_openai(
    creds: dict,
    system_prompt: str,
    user_prompt: str,
    model: str,
    timeout_s: float,
    base_url: str,
    extra_headers: Optional[dict[str, str]] = None,
) -> Optional[str]:
    key = creds.get("api_key", "")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if choices:
            return (choices[0].get("message", {}).get("content") or "").strip() or None
        return None


async def _complete_gemini(creds: dict, system_prompt: str, user_prompt: str, model: str, timeout_s: float) -> Optional[str]:
    key = creds.get("api_key", "")
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            },
        )
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return (parts[0].get("text") or "").strip() or None
        return None


async def _complete_vertex_gemini(
    creds: dict, system_prompt: str, user_prompt: str, model: str, timeout_s: float
) -> Optional[str]:
    """Gemini through Vertex AI with the signed-in Google account's token."""
    token = creds.get("access_token", "")
    project = str(creds.get("project_id") or "").strip()
    if not token or not project:
        return None
    location = vertex_location(creds)
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}:generateContent"
    )
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            },
        )
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return (parts[0].get("text") or "").strip() or None
        return None


# ---------------------------------------------------------------------------
# Connected LLM models for the picker
# ---------------------------------------------------------------------------

def connected_llm_models() -> list[dict[str, str]]:
    """Return model options for connected LLM providers so the Ask picker
    can list them alongside the built-in default."""
    from app.integrations import llm_client

    models: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(model_id: str, label: str) -> None:
        if model_id and model_id not in seen:
            seen.add(model_id)
            models.append({"id": model_id, "label": label})

    if get_connection("anthropic"):
        add("anthropic:claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (your key)")
        add("anthropic:claude-3-5-haiku-20241022", "Claude 3.5 Haiku (your key)")
    if get_connection("openai"):
        add("openai:gpt-4o", "GPT-4o (your OpenAI key)")
    if get_connection("gemini_oauth"):
        add("gemini_oauth:gemini-2.0-flash", "Gemini 2.0 Flash (signed in with Google)")
        add("gemini_oauth:gemini-1.5-pro", "Gemini 1.5 Pro (signed in with Google)")
    if get_connection("gemini"):
        add("gemini:gemini-1.5-flash", "Gemini 1.5 Flash (your key)")
    if get_connection("mistral"):
        add("mistral:mistral-large-latest", "Mistral Large (your key)")
    if get_connection("groq"):
        add("groq:llama-3.3-70b-versatile", "Llama 3.3 70B · Groq")
        add("groq:llama-3.1-8b-instant", "Llama 3.1 8B Instant · Groq")
    if get_creds("openrouter"):
        for item in llm_client.CURATED_MODELS:
            add(item["id"], f"{item['label']} · OpenRouter")
        creds = get_creds("openrouter") or {}
        default = str(creds.get("default_model") or os.environ.get("ASK_MODEL") or "").strip()
        if default:
            add(default, f"{default} (Ask default · OpenRouter)")
        for env_name, label in (("DETECTION_MODEL", "Detection"), ("DRAFTING_MODEL", "Drafting")):
            mid = os.environ.get(env_name, "").strip()
            if mid:
                add(mid, f"{mid} ({label} · OpenRouter)")
    if get_connection("claude_custom"):
        add("claude_custom:gpt-4o", "Custom endpoint (your key)")
    return models
