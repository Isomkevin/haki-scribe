"""Omi Miniapp pairing: link wearable users and resolve desk sessions.

Persist via the integrations connection store (provider ``omi``) so the
uid map survives the same snapshot / Postgres path as other connectors.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from app.models.schemas import Session, SessionSource, SessionStatus
from app.services import integrations, storage

logger = logging.getLogger(__name__)

PROVIDER_ID = "omi"


class OmiPairingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def public_base_url() -> str:
    return (
        os.environ.get("BACKEND_INTERNAL_URL")
        or os.environ.get("HAKISCRIBE_API")
        or "https://hakiscribe-backend.onrender.com"
    ).rstrip("/")


def webhook_url() -> str:
    return f"{public_base_url()}/webhooks/omi"


def auth_url() -> str:
    return f"{public_base_url()}/integrations/omi/auth"


def setup_completed_url() -> str:
    return f"{public_base_url()}/integrations/omi/setup-completed"


def _creds() -> dict[str, Any]:
    return dict(integrations.get_creds(PROVIDER_ID) or {})


def linked_uid() -> Optional[str]:
    uid = str((_creds().get("uid") or "")).strip()
    return uid or None


def is_linked(uid: str | None) -> bool:
    needle = (uid or "").strip()
    if not needle:
        return False
    current = linked_uid()
    return bool(current and current == needle)


def setup_completed(uid: str | None) -> bool:
    return is_linked(uid)


def link_uid(uid: str) -> dict[str, Any]:
    cleaned = (uid or "").strip()
    if not cleaned:
        raise OmiPairingError("Missing uid.", status_code=400)
    creds = _creds()
    previous = str(creds.get("uid") or "").strip()
    if previous and previous != cleaned:
        # New Omi user replaces the previous link on this single-tenant demo desk.
        creds["omi_conversation_ids"] = {}
        creds.pop("active_session_id", None)
    creds["uid"] = cleaned
    creds["linked_at"] = datetime.utcnow().isoformat()
    creds.setdefault("omi_conversation_ids", {})
    integrations.save_connection(PROVIDER_ID, creds)
    return status_payload()


def unlink() -> bool:
    return integrations.remove_connection(PROVIDER_ID)


def touch_activity(*, session_id: uuid.UUID | None = None, omi_session_id: str | None = None) -> None:
    creds = _creds()
    if not creds.get("uid"):
        return
    creds["last_activity_at"] = datetime.utcnow().isoformat()
    if session_id is not None:
        creds["active_session_id"] = str(session_id)
    if omi_session_id:
        mapping = dict(creds.get("omi_conversation_ids") or {})
        if session_id is not None:
            mapping[str(omi_session_id)] = str(session_id)
        creds["omi_conversation_ids"] = mapping
    integrations.save_connection(PROVIDER_ID, creds)


def _parse_uuid(value: str | None) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _session_from_detail(detail) -> Session:
    return Session(
        id=detail.id,
        title=detail.title,
        source=detail.source,
        language_hint=detail.language_hint,
        status=detail.status,
        created_at=detail.created_at,
        updated_at=detail.updated_at,
    )


def _find_session_for_omi_conversation(omi_session_id: str) -> Optional[Session]:
    creds = _creds()
    mapping = creds.get("omi_conversation_ids") or {}
    mapped = mapping.get(str(omi_session_id))
    sid = _parse_uuid(mapped)
    if sid is None:
        return None
    detail = storage.get_session(sid)
    return _session_from_detail(detail) if detail else None


def _find_open_omi_session_for_uid(uid: str) -> Optional[Session]:
    active = _parse_uuid(str((_creds().get("active_session_id") or "")))
    if active:
        detail = storage.get_session(active)
        if detail and detail.source == SessionSource.omi and detail.status == SessionStatus.recording:
            return _session_from_detail(detail)
    for item in storage.list_library_sessions():
        if item.source != SessionSource.omi or item.status != SessionStatus.recording:
            continue
        detail = storage.get_session(item.id)
        if detail is None:
            continue
        for seg in detail.transcript:
            raw = seg.source_raw or {}
            if str(raw.get("omi_uid") or "") == uid:
                return _session_from_detail(detail)
    return None


def resolve_session(
    *,
    session_ref: str | None,
    uid: str | None,
    memory_title: str | None = None,
    is_memory: bool = False,
) -> Session:
    """Resolve a HakiScribe session for an Omi webhook post.

    ``session_ref`` may be a HakiScribe UUID (legacy paste URL) or an Omi
    conversation id from the Miniapp realtime path.
    """
    cleaned_uid = (uid or "").strip() or None
    hakiscribe_id = _parse_uuid(session_ref)

    if hakiscribe_id is not None:
        detail = storage.get_session(hakiscribe_id)
        if detail is not None:
            session = _session_from_detail(detail)
            if cleaned_uid:
                touch_activity(session_id=session.id, omi_session_id=None)
            return session
        # UUID-shaped but unknown — fall through if we have a linked uid.

    omi_conversation_id = None if hakiscribe_id is not None and storage.get_session(hakiscribe_id) else session_ref

    if cleaned_uid:
        if not is_linked(cleaned_uid):
            raise OmiPairingError(
                "Omi is not connected for this uid. Open Connectors and complete Miniapp auth.",
                status_code=403,
            )
        if omi_conversation_id:
            existing = _find_session_for_omi_conversation(str(omi_conversation_id))
            if existing is not None:
                touch_activity(session_id=existing.id, omi_session_id=str(omi_conversation_id))
                return existing
        if not is_memory:
            open_session = _find_open_omi_session_for_uid(cleaned_uid)
            if open_session is not None:
                touch_activity(
                    session_id=open_session.id,
                    omi_session_id=str(omi_conversation_id) if omi_conversation_id else None,
                )
                return open_session

        title = (memory_title or "").strip() or (
            f"Omi · {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC"
        )
        session = storage.create_session(
            Session(
                title=title[:200],
                source=SessionSource.omi,
                language_hint="code-switch",
                status=SessionStatus.ready if is_memory else SessionStatus.recording,
            )
        )
        touch_activity(
            session_id=session.id,
            omi_session_id=str(omi_conversation_id) if omi_conversation_id else None,
        )
        return session

    if hakiscribe_id is not None:
        raise OmiPairingError("Session not found", status_code=404)

    raise OmiPairingError(
        "Missing session_id. Pair Omi with /webhooks/omi?session_id=<HakiScribe session UUID>, "
        "or connect the Miniapp so posts include a linked uid.",
        status_code=400,
    )


def status_payload() -> dict[str, Any]:
    creds = _creds()
    uid = linked_uid()
    conn = integrations.get_connection(PROVIDER_ID)
    return {
        "linked": bool(uid),
        "uid": uid,
        "masked_uid": integrations._mask(uid) if uid else None,  # noqa: SLF001
        "connected_at": (conn or {}).get("connected_at") or creds.get("linked_at"),
        "last_activity_at": creds.get("last_activity_at"),
        "active_session_id": creds.get("active_session_id"),
        "webhook_url": webhook_url(),
        "auth_url": auth_url(),
        "setup_completed_url": setup_completed_url(),
    }
