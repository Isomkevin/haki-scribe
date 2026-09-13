"""
Demo-grade store so the whole pipeline works with zero external setup.
State lives in memory and is snapshotted to a JSON file so a process
restart (local reload, same Render instance) does not wipe the library.
Swap the function bodies for Supabase before relying on this past the
hackathon — signatures stay the same.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
_STORE_PATH = Path(os.environ.get("HAKISCRIBE_STORE", "data/store.json"))

from app.services import db, object_store

from app.models.schemas import (
    ActionResult,
    ActionStatus,
    Contact,
    DetectedAction,
    FlaggedMoment,
    Matter,
    Session,
    SessionDetail,
    SessionLibraryItem,
    TranscriptSegment,
)

_sessions: dict[uuid.UUID, Session] = {}
_transcripts: dict[uuid.UUID, list[TranscriptSegment]] = {}
_actions: dict[uuid.UUID, list[DetectedAction]] = {}
_flags: dict[uuid.UUID, list[FlaggedMoment]] = {}
_matters: dict[uuid.UUID, Matter] = {}
_contacts: dict[uuid.UUID, Contact] = {}
_results: dict[uuid.UUID, list[ActionResult]] = {}
_session_matter_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
_session_contact_ids: dict[uuid.UUID, list[uuid.UUID]] = {}


def _session_matters(session_id: uuid.UUID) -> list[Matter]:
    return [_matters[mid] for mid in _session_matter_ids.get(session_id, []) if mid in _matters]


def _session_contacts(session_id: uuid.UUID) -> list[Contact]:
    return [_contacts[cid] for cid in _session_contact_ids.get(session_id, []) if cid in _contacts]


def create_session(session: Session) -> Session:
    _sessions[session.id] = session
    _transcripts[session.id] = []
    _actions[session.id] = []
    _flags[session.id] = []
    _results[session.id] = []
    _session_matter_ids[session.id] = []
    _session_contact_ids[session.id] = []
    _persist()
    return session


def get_session(session_id: uuid.UUID) -> Optional[SessionDetail]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    return SessionDetail(
        **session.model_dump(),
        transcript=_transcripts[session_id],
        detected_actions=_actions.get(session_id, []),
        flagged_moments=_flags.get(session_id, []),
        action_results=_results.get(session_id, []),
        matters=_session_matters(session_id),
        contacts=_session_contacts(session_id),
    )


def list_sessions() -> list[Session]:
    return list(_sessions.values())


def _generated_types(session_id: uuid.UUID) -> list[str]:
    types: list[str] = []
    for result in _results.get(session_id, []):
        if result.status == "success" and result.type.value not in types:
            types.append(result.type.value)
    return types


def list_library_sessions() -> list[SessionLibraryItem]:
    items = [
        SessionLibraryItem(
            **session.model_dump(),
            matters=_session_matters(session.id),
            contacts=_session_contacts(session.id),
            generated_types=_generated_types(session.id),
        )
        for session in _sessions.values()
    ]
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def update_session_status(session_id: uuid.UUID, status) -> Optional[Session]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.status = status
    _persist()
    return session


def append_segment(session_id: uuid.UUID, segment: TranscriptSegment) -> None:
    _transcripts.setdefault(session_id, []).append(segment)
    _persist()


def get_transcript(session_id: uuid.UUID) -> list[TranscriptSegment]:
    return _transcripts.get(session_id, [])


def set_detected_actions(session_id: uuid.UUID, actions: list[DetectedAction]) -> None:
    _actions[session_id] = actions
    _persist()


def get_detected_actions(session_id: uuid.UUID) -> list[DetectedAction]:
    return _actions.get(session_id, [])


def get_action(session_id: uuid.UUID, action_id: uuid.UUID) -> Optional[DetectedAction]:
    for action in _actions.get(session_id, []):
        if action.id == action_id:
            return action
    return None


def update_action_fields(session_id: uuid.UUID, action_id: uuid.UUID, fields: dict) -> Optional[DetectedAction]:
    action = get_action(session_id, action_id)
    if action is None:
        return None
    action.extracted_fields = {**action.extracted_fields, **fields}
    return action


def update_action_status(session_id: uuid.UUID, action_id: uuid.UUID, status: ActionStatus) -> Optional[DetectedAction]:
    for action in _actions.get(session_id, []):
        if action.id == action_id:
            action.status = status
            _persist()
            return action
    return None


def _archive_document(session_id: uuid.UUID, result: ActionResult) -> None:
    """Keep the firm's own durable copy of a drafted document in S3 when configured."""
    text = result.result.get("document_text") if isinstance(result.result, dict) else None
    if not isinstance(text, str) or not text.strip() or result.result.get("s3_url"):
        return
    kind = str(result.result.get("document_kind") or "document").replace(" ", "-")
    key = f"sessions/{session_id}/{kind}-{result.action_id}.txt"
    url = object_store.archive_document(key, text)
    if url:
        result.result["s3_key"] = key
        result.result["s3_url"] = url


def upsert_action_results(session_id: uuid.UUID, results: list[ActionResult]) -> list[ActionResult]:
    existing = {item.action_id: item for item in _results.get(session_id, [])}
    for result in results:
        if result.status == "success":
            _archive_document(session_id, result)
        existing[result.action_id] = result
    merged = list(existing.values())
    _results[session_id] = merged
    _persist()
    return merged


def get_action_results(session_id: uuid.UUID) -> list[ActionResult]:
    return _results.get(session_id, [])


def add_flag(session_id: uuid.UUID, flag: FlaggedMoment) -> None:
    _flags.setdefault(session_id, []).append(flag)
    _persist()


def get_flags(session_id: uuid.UUID) -> list[FlaggedMoment]:
    return _flags.get(session_id, [])


def relabel_speakers(session_id: uuid.UUID, mapping: dict[str, str]) -> list[TranscriptSegment]:
    segments = _transcripts.get(session_id, [])
    cleaned = {key: value.strip() for key, value in mapping.items() if value and value.strip()}
    for segment in segments:
        if segment.speaker in cleaned:
            segment.speaker = cleaned[segment.speaker]
    _persist()
    return segments


def set_segment_redacted(session_id: uuid.UUID, segment_id: uuid.UUID, redacted: bool) -> Optional[TranscriptSegment]:
    for segment in _transcripts.get(session_id, []):
        if segment.id == segment_id:
            segment.redacted = redacted
            _persist()
            return segment
    return None


def update_segment(session_id: uuid.UUID, segment_id: uuid.UUID, *, redacted: Optional[bool] = None, text: Optional[str] = None) -> Optional[TranscriptSegment]:
    for segment in _transcripts.get(session_id, []):
        if segment.id == segment_id:
            if redacted is not None:
                segment.redacted = redacted
            if text is not None:
                segment.text = text
            _persist()
            return segment
    return None


def create_matter(matter: Matter) -> Matter:
    _matters[matter.id] = matter
    for session_id in matter.session_ids:
        link_matter_to_session(session_id, matter.id)
    _persist()
    return matter


def get_matter(matter_id: uuid.UUID) -> Optional[Matter]:
    return _matters.get(matter_id)


def list_matters() -> list[Matter]:
    return list(_matters.values())


def find_matter_by_client(client_name: str) -> Optional[Matter]:
    """Best-effort case-insensitive match — good enough for a demo; swap
    for real fuzzy matching against the CRM/Workspace client list later."""
    needle = client_name.strip().lower()
    for matter in _matters.values():
        if needle and needle in matter.client_name.lower():
            return matter
    return None


def link_matter_to_session(session_id: uuid.UUID, matter_id: uuid.UUID) -> None:
    ids = _session_matter_ids.setdefault(session_id, [])
    if matter_id not in ids:
        ids.append(matter_id)
    matter = _matters.get(matter_id)
    if matter is not None and session_id not in matter.session_ids:
        matter.session_ids.append(session_id)


def create_contact(contact: Contact) -> Contact:
    _contacts[contact.id] = contact
    if contact.session_id is not None:
        link_contact_to_session(contact.session_id, contact.id)
    if contact.matter_id is not None:
        matter = _matters.get(contact.matter_id)
        if matter is not None and contact.id not in matter.contact_ids:
            matter.contact_ids.append(contact.id)
    _persist()
    return contact


def get_contact(contact_id: uuid.UUID) -> Optional[Contact]:
    return _contacts.get(contact_id)


def list_contacts() -> list[Contact]:
    return list(_contacts.values())


def find_contact_by_name(name: str) -> Optional[Contact]:
    needle = name.strip().lower()
    for contact in _contacts.values():
        if needle and contact.name.strip().lower() == needle:
            return contact
    return None


def link_contact_to_session(session_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    ids = _session_contact_ids.setdefault(session_id, [])
    if contact_id not in ids:
        ids.append(contact_id)
    contact = _contacts.get(contact_id)
    if contact is not None and contact.session_id is None:
        contact.session_id = session_id


def _uuid_map(raw: dict) -> dict[uuid.UUID, list[uuid.UUID]]:
    return {uuid.UUID(key): [uuid.UUID(item) for item in value] for key, value in raw.items()}


def _snapshot() -> dict:
    from app.services import integrations
    return {
            "sessions": [session.model_dump(mode="json") for session in _sessions.values()],
            "transcripts": {str(key): [item.model_dump(mode="json") for item in value] for key, value in _transcripts.items()},
            "actions": {str(key): [item.model_dump(mode="json") for item in value] for key, value in _actions.items()},
            "flags": {str(key): [item.model_dump(mode="json") for item in value] for key, value in _flags.items()},
            "results": {str(key): [item.model_dump(mode="json") for item in value] for key, value in _results.items()},
            "matters": [item.model_dump(mode="json") for item in _matters.values()],
            "contacts": [item.model_dump(mode="json") for item in _contacts.values()],
            "integrations": integrations.connections_snapshot(),
            "session_matter_ids": {str(key): [str(item) for item in value] for key, value in _session_matter_ids.items()},
            "session_contact_ids": {str(key): [str(item) for item in value] for key, value in _session_contact_ids.items()},
    }


def _persist() -> None:
    payload = _snapshot()
    # Durable store first — the JSON file is only a local convenience mirror.
    db.save_snapshot(payload)
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
        tmp.replace(_STORE_PATH)
    except Exception as exc:  # noqa: BLE001 — persistence must never break the API
        logger.warning("Could not persist HakiScribe store: %s", exc)


def _load() -> None:
    payload = db.load_snapshot()
    if payload is None:
        if not _STORE_PATH.exists():
            return
        try:
            payload = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load HakiScribe store: %s", exc)
            return
        # First run against a fresh database: carry the local snapshot over.
        _restore(payload)
        db.save_snapshot(_snapshot())
        return
    _restore(payload)


def _restore(payload: dict) -> None:
    from app.services import integrations
    _sessions.update({item.id: item for item in (Session(**raw) for raw in payload.get("sessions", []))})
    for key, value in payload.get("transcripts", {}).items():
        _transcripts[uuid.UUID(key)] = [TranscriptSegment(**item) for item in value]
    for key, value in payload.get("actions", {}).items():
        _actions[uuid.UUID(key)] = [DetectedAction(**item) for item in value]
    for key, value in payload.get("flags", {}).items():
        _flags[uuid.UUID(key)] = [FlaggedMoment(**item) for item in value]
    for key, value in payload.get("results", {}).items():
        _results[uuid.UUID(key)] = [ActionResult(**item) for item in value]
    _matters.update({item.id: item for item in (Matter(**raw) for raw in payload.get("matters", []))})
    _contacts.update({item.id: item for item in (Contact(**raw) for raw in payload.get("contacts", []))})
    _session_matter_ids.update(_uuid_map(payload.get("session_matter_ids", {})))
    _session_contact_ids.update(_uuid_map(payload.get("session_contact_ids", {})))
    integrations.restore_connections(payload.get("integrations", []))


_load()
