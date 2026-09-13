"""
Thin client for Ambiguous AI's workspace REST API — this is what turns
draft_document, calendar_event, workspace_matter, and crm_entry from
local-only stubs into artifacts that land in real running apps (Docs,
Calendar, CRM), plus a Chat notification when something's ready for
review.

Every function no-ops (returns None) if AMBIGUOUS_API_KEY isn't set, so
the rest of the pipeline works identically with or without a configured
workspace — same graceful-degradation pattern as the ASR/OpenRouter keys.

Live OpenAPI (https://app.ambiguous.ai/api/openapi.json) is the source of
truth for field names. The marketing curl examples still show an older
block-array document body and start/end event fields; those 422.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://app.ambiguous.ai/api"
WORKSPACE_URL = os.environ.get("AMBIGUOUS_WORKSPACE_URL", "https://app.ambiguous.ai")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_last_error: str | None = None


def configured() -> bool:
    return bool(_api_key())


def last_error() -> str | None:
    return _last_error


def document_url(document_id: str | None) -> str | None:
    return f"{WORKSPACE_URL}/docs/{document_id}" if document_id else None


def event_url(event_id: str | None) -> str | None:
    return f"{WORKSPACE_URL}/calendar/{event_id}" if event_id else None


def deal_url(deal_id: str | None) -> str | None:
    return f"{WORKSPACE_URL}/crm/deals/{deal_id}" if deal_id else None


def contact_url(contact_id: str | None) -> str | None:
    return f"{WORKSPACE_URL}/crm/contacts/{contact_id}" if contact_id else None


def _api_key() -> Optional[str]:
    return os.environ.get("AMBIGUOUS_API_KEY") or None


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}


def _set_error(message: str) -> None:
    global _last_error
    _last_error = message
    logger.warning("Ambiguous AI %s; keeping local result", message)


def _as_iso(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return raw
    if raw.endswith("Z") or (len(raw) > 10 and ("+" in raw[10:] or raw.endswith("z"))):
        return raw
    if "T" in raw:
        return f"{raw}Z"
    return raw


def _as_resource(data: Any) -> Optional[dict[str, Any]]:
    if isinstance(data, dict):
        if data.get("id"):
            return data
        for key in ("data", "document", "event", "contact", "deal", "calendar", "message"):
            inner = data.get(key)
            if isinstance(inner, dict) and inner.get("id"):
                return inner
            if isinstance(inner, list) and inner:
                found = _as_resource(inner[0])
                if found:
                    return found
        return data or None
    if isinstance(data, list) and data:
        return _as_resource(data[0])
    return None


async def _request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Optional[dict[str, Any]]:
    """Never raise into generation — local artifacts stay usable if the
    workspace mirror fails."""
    global _last_error
    if not _api_key():
        return None
    _last_error = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{BASE_URL}{path}",
                headers=_headers(),
                json=payload,
            )
            if resp.status_code == 409:
                conflict = resp.json() if resp.content else {}
                existing_id = (
                    conflict.get("deal_id")
                    or conflict.get("contact_id")
                    or conflict.get("id")
                    or (conflict.get("deal") or {}).get("id")
                    or (conflict.get("contact") or {}).get("id")
                )
                if existing_id:
                    return {"id": existing_id, **{k: v for k, v in conflict.items() if k != "error"}}
            if resp.status_code >= 400:
                _set_error(f"{method} {path} -> {resp.status_code}: {resp.text[:240]}")
                return None
            if not resp.content:
                return {}
            return _as_resource(resp.json())
    except Exception as exc:  # noqa: BLE001
        _set_error(f"{method} {path} failed ({exc})")
        return None


async def ping() -> bool:
    """True when the key can actually reach the workspace API."""
    if not _api_key():
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/documents", headers=_headers())
            return resp.status_code < 400
    except Exception:  # noqa: BLE001
        return False


async def create_document(title: str, body_text: str) -> Optional[dict[str, Any]]:
    """POST /api/documents — CreateDocumentInput.content is Markdown, not blocks."""
    markdown = f"# {title}\n\n{body_text.strip()}"
    return await _request("POST", "/documents", {"type": "doc", "title": title, "content": markdown})


async def _default_calendar_id() -> Optional[str]:
    configured_id = os.environ.get("AMBIGUOUS_CALENDAR_ID") or ""
    if configured_id.strip():
        return configured_id.strip()
    calendar = await _request("GET", "/calendars")
    return (calendar or {}).get("id")


async def create_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str,
    description: str | None = None,
) -> Optional[dict[str, Any]]:
    """POST /api/calendars/{id}/events — EventCreateInput uses start_at/end_at."""
    calendar_id = await _default_calendar_id()
    if not calendar_id:
        _set_error("GET /calendars returned no calendar id")
        return None
    payload: dict[str, Any] = {
        "title": title,
        "start_at": _as_iso(start_iso),
        "end_at": _as_iso(end_iso),
        "force": True,
    }
    if description:
        payload["description"] = description
    return await _request("POST", f"/calendars/{calendar_id}/events", payload)


async def create_deal(matter_name: str, client_name: str) -> Optional[dict[str, Any]]:
    """POST /api/crm/deals — DealCreateInput.title is the deal name."""
    return await _request(
        "POST",
        "/crm/deals",
        {
            "title": matter_name,
            "custom_properties": {"client_name": client_name, "source": "hakiscribe"},
        },
    )


async def update_deal(deal_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    """PATCH /api/crm/deals/:id — link a new session to an existing matter."""
    if "name" in fields and "title" not in fields:
        fields["title"] = fields.pop("name")
    return await _request("PATCH", f"/crm/deals/{deal_id}", fields)


async def create_contact(contact_name: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
    """POST /api/crm/contacts — ContactCreateInput rejects unknown fields."""
    payload: dict[str, Any] = {"name": contact_name, "type": "person"}
    extras: dict[str, Any] = {}
    if isinstance(updates, dict):
        for key in ("email", "phone", "title", "website", "industry", "first_name", "last_name"):
            if updates.get(key):
                payload[key] = updates[key]
        extras = {
            key: value
            for key, value in updates.items()
            if key not in payload and value not in (None, "")
        }
    if extras:
        payload["custom_properties"] = extras
    return await _request("POST", "/crm/contacts", payload)


async def post_chat_message(content: str, channel: Optional[str] = None) -> Optional[dict[str, Any]]:
    """POST /api/channels/:id/messages — channel id is a UUID, not 'general'."""
    channel = channel or os.environ.get("AMBIGUOUS_NOTIFY_CHANNEL") or ""
    if not _UUID_RE.match(channel.strip()):
        logger.info("Skipping Ambiguous chat ping; AMBIGUOUS_NOTIFY_CHANNEL is not a channel UUID")
        return None
    return await _request("POST", f"/channels/{channel.strip()}/messages", {"content": content})
