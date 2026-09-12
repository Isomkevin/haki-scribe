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

import os
from typing import Any, Optional

import httpx

BASE_URL = "https://app.ambiguous.ai/api"


def _api_key() -> Optional[str]:
    return os.environ.get("AMBIGUOUS_API_KEY") or None


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}


async def create_document(title: str, body_text: str) -> Optional[dict[str, Any]]:
    """POST /api/documents — used for draft_document. Splits body_text into
    paragraph blocks; good enough for a legal letter/memo draft."""
    if not _api_key():
        return None
    content = [{"type": "heading", "level": 1, "text": title}]
    content += [{"type": "paragraph", "text": p} for p in body_text.split("\n") if p.strip()]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/documents", headers=_headers(), json={"type": "doc", "title": title, "content": content}
        )
        resp.raise_for_status()
        return resp.json()


async def create_calendar_event(title: str, start_iso: str, end_iso: str) -> Optional[dict[str, Any]]:
    """POST /api/calendar/events — used for calendar_event, alongside the
    .ics we already generate locally as a portable fallback."""
    if not _api_key():
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/calendar/events",
            headers=_headers(),
            json={"title": title, "start": start_iso, "end": end_iso},
        )
        resp.raise_for_status()
        return resp.json()


async def create_deal(matter_name: str, client_name: str) -> Optional[dict[str, Any]]:
    """POST /api/crm/deals — a 'matter' maps naturally onto a CRM deal."""
    if not _api_key():
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/crm/deals",
            headers=_headers(),
            json={"name": matter_name, "client_name": client_name},
        )
        resp.raise_for_status()
        return resp.json()


async def update_deal(deal_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    """PATCH /api/crm/deals/:id — link a new session to an existing matter."""
    if not _api_key():
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(f"{BASE_URL}/crm/deals/{deal_id}", headers=_headers(), json=fields)
        resp.raise_for_status()
        return resp.json()


async def create_contact(contact_name: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Best-effort CRM contact creation. The public API reference lists
    GET /api/crm/contacts explicitly but not the POST route — this follows
    the same CRUD convention as every other module. Confirm the exact path
    against Ambiguous's live API reference/Scalar docs before relying on it;
    swap the path here if it differs."""
    if not _api_key():
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/crm/contacts",
            headers=_headers(),
            json={"name": contact_name, **updates},
        )
        resp.raise_for_status()
        return resp.json()


async def post_chat_message(content: str, channel: Optional[str] = None) -> Optional[dict[str, Any]]:
    """POST /api/channels/:id/messages — used to notify a human that a
    draft is ready for review, instead of ever auto-sending legal work
    product (e.g. via Mail) without a person in the loop."""
    if not _api_key():
        return None
    channel = channel or os.environ.get("AMBIGUOUS_NOTIFY_CHANNEL", "general")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/channels/{channel}/messages", headers=_headers(), json={"content": content}
        )
        resp.raise_for_status()
        return resp.json()
