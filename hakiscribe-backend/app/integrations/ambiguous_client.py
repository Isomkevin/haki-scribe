"""
Thin client for Ambiguous AI's workspace REST API — this is what turns
draft_document, calendar_event, workspace_matter, and crm_entry from
local-only stubs into artifacts that land in real running apps (Docs,
Calendar, CRM), plus a Chat notification when something's ready for
review.

Every function no-ops (returns None) if AMBIGUOUS_API_KEY isn't set, so
the rest of the pipeline works identically with or without a configured
workspace — same graceful-degradation pattern as the ASR/OpenRouter keys.

Base API reference: https://www.ambiguous.ai/agents/api
"""

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://app.ambiguous.ai/api"
WORKSPACE_URL = os.environ.get("AMBIGUOUS_WORKSPACE_URL", "https://app.ambiguous.ai")


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


async def _request(method: str, path: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Never raise into generation — local artifacts stay usable if the
    workspace mirror fails."""
    if not _api_key():
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, f"{BASE_URL}{path}", headers=_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ambiguous AI %s %s failed (%s); keeping local result", method, path, exc)
        return None


async def create_document(title: str, body_text: str) -> Optional[dict[str, Any]]:
    """POST /api/documents — used for draft_document. Splits body_text into
    paragraph blocks; good enough for a legal letter/memo draft."""
    content = [{"type": "heading", "level": 1, "text": title}]
    content += [{"type": "paragraph", "text": p} for p in body_text.split("\n") if p.strip()]
    return await _request("POST", "/documents", {"type": "doc", "title": title, "content": content})


async def create_calendar_event(title: str, start_iso: str, end_iso: str) -> Optional[dict[str, Any]]:
    """POST /api/calendar/events — used for calendar_event, alongside the
    .ics we already generate locally as a portable fallback."""
    return await _request("POST", "/calendar/events", {"title": title, "start": start_iso, "end": end_iso})


async def create_deal(matter_name: str, client_name: str) -> Optional[dict[str, Any]]:
    """POST /api/crm/deals — a 'matter' maps naturally onto a CRM deal."""
    return await _request("POST", "/crm/deals", {"name": matter_name, "client_name": client_name})


async def update_deal(deal_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    """PATCH /api/crm/deals/:id — link a new session to an existing matter."""
    return await _request("PATCH", f"/crm/deals/{deal_id}", fields)


async def create_contact(contact_name: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Best-effort CRM contact creation. The public API reference lists
    GET /api/crm/contacts explicitly but not the POST route — this follows
    the same CRUD convention as every other module. Confirm the exact path
    against Ambiguous's live API reference/Scalar docs before relying on it;
    swap the path here if it differs."""
    return await _request("POST", "/crm/contacts", {"name": contact_name, **updates})


async def post_chat_message(content: str, channel: Optional[str] = None) -> Optional[dict[str, Any]]:
    """POST /api/channels/:id/messages — used to notify a human that a
    draft is ready for review, instead of ever auto-sending legal work
    product (e.g. via Mail) without a person in the loop."""
    channel = channel or os.environ.get("AMBIGUOUS_NOTIFY_CHANNEL", "general")
    return await _request("POST", f"/channels/{channel}/messages", {"content": content})
