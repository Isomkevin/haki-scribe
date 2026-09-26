"""
Shared persistence for matters and linked contacts.

Both POST /matters (and /contacts) and the workspace_matter / crm_entry
generators call these helpers so Session Library and the Matters endpoint
stay in lockstep.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from app.models.schemas import Contact, Matter
from app.services import storage


def persist_matter(
    *,
    client_name: str,
    matter_name: str,
    session_id: Optional[uuid.UUID] = None,
    existing_matter_id: Optional[str] = None,
    ambiguous_deal_id: Optional[str] = None,
) -> tuple[Matter, str]:
    """Create or link a Matter. Returns (matter, 'created' | 'linked')."""
    existing: Optional[Matter] = None
    if existing_matter_id:
        try:
            existing = storage.get_matter(uuid.UUID(str(existing_matter_id)))
        except ValueError:
            existing = next((item for item in storage.list_matters() if str(item.id) == str(existing_matter_id)), None)
    if existing is None and client_name:
        existing = storage.find_matter_by_client(client_name)

    if existing is not None:
        if matter_name and matter_name != existing.matter_name:
            existing.matter_name = matter_name
        if client_name and not existing.client_name:
            existing.client_name = client_name
        if ambiguous_deal_id and not existing.ambiguous_deal_id:
            existing.ambiguous_deal_id = ambiguous_deal_id
        if session_id is not None:
            storage.link_matter_to_session(session_id, existing.id)
        return existing, "linked"

    matter = Matter(
        client_name=client_name or matter_name,
        matter_name=matter_name or client_name or "Untitled matter",
        session_ids=[session_id] if session_id is not None else [],
        ambiguous_deal_id=ambiguous_deal_id,
    )
    storage.create_matter(matter)
    return matter, "created"


def persist_contact(
    *,
    name: str,
    updates: Optional[dict[str, Any]] = None,
    session_id: Optional[uuid.UUID] = None,
    matter_id: Optional[uuid.UUID] = None,
    ambiguous_contact_id: Optional[str] = None,
) -> Contact:
    """Create or reuse a contact and attach it to the session/matter."""
    cleaned = (name or "").strip()
    if not cleaned:
        cleaned = "Unnamed contact"

    existing = storage.find_contact_by_name(cleaned)
    if existing is not None:
        if updates:
            existing.updates = {**existing.updates, **updates}
        if matter_id is not None:
            existing.matter_id = existing.matter_id or matter_id
            matter = storage.get_matter(matter_id)
            if matter is not None and existing.id not in matter.contact_ids:
                matter.contact_ids.append(existing.id)
        if session_id is not None:
            storage.link_contact_to_session(session_id, existing.id)
        if ambiguous_contact_id and not existing.ambiguous_contact_id:
            existing.ambiguous_contact_id = ambiguous_contact_id
        storage.persist()
        return existing

    contact = Contact(
        name=cleaned,
        updates=updates or {},
        matter_id=matter_id,
        session_id=session_id,
        ambiguous_contact_id=ambiguous_contact_id,
    )
    return storage.create_contact(contact)


_GENERIC_SPEAKER = re.compile(
    r"^(speaker|spk|voice|person|participant|unknown|user|you|me|guest)?[\s_#-]*\d*$|^speaker[\s_#-]*[a-z0-9]{1,3}$",
    re.IGNORECASE,
)


def capture_speaker_contacts(session_id: uuid.UUID) -> list[Contact]:
    """Turn named transcript speakers (mic or Omi) into contacts linked to the
    session, so everyone who spoke shows up in the tracker automatically.
    Generic labels like "Speaker 1" are skipped until the lawyer renames them."""
    detail = storage.get_session(session_id)
    if detail is None:
        return []
    source = getattr(detail.source, "value", str(detail.source))
    seen: set[str] = set()
    captured: list[Contact] = []
    for segment in detail.transcript:
        name = (segment.speaker or "").strip()
        if not name or len(name) < 2 or _GENERIC_SPEAKER.match(name) or name.lower() in seen:
            continue
        seen.add(name.lower())
        existing = storage.find_contact_by_name(name)
        updates = None if existing else {"source": f"{source}_transcription"}
        matter_id = detail.matters[0].id if detail.matters and existing is None else None
        captured.append(persist_contact(name=name, updates=updates, session_id=session_id, matter_id=matter_id))
    return captured
