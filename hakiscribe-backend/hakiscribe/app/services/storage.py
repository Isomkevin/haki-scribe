"""
Demo-grade in-memory store so the whole pipeline works with zero external
setup. Swap this for real Supabase reads/writes before relying on it past
the hackathon — the function signatures are written so that swap doesn't
touch any router code.
"""

import uuid
from typing import Optional

from app.models.schemas import (
    ActionStatus,
    DetectedAction,
    FlaggedMoment,
    Matter,
    Session,
    SessionDetail,
    TranscriptSegment,
)

_sessions: dict[uuid.UUID, Session] = {}
_transcripts: dict[uuid.UUID, list[TranscriptSegment]] = {}
_actions: dict[uuid.UUID, list[DetectedAction]] = {}
_flags: dict[uuid.UUID, list[FlaggedMoment]] = {}
_matters: dict[uuid.UUID, Matter] = {}


def create_session(session: Session) -> Session:
    _sessions[session.id] = session
    _transcripts[session.id] = []
    _actions[session.id] = []
    _flags[session.id] = []
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
    )


def list_sessions() -> list[Session]:
    return list(_sessions.values())


def update_session_status(session_id: uuid.UUID, status) -> Optional[Session]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.status = status
    return session


def append_segment(session_id: uuid.UUID, segment: TranscriptSegment) -> None:
    _transcripts.setdefault(session_id, []).append(segment)


def get_transcript(session_id: uuid.UUID) -> list[TranscriptSegment]:
    return _transcripts.get(session_id, [])


def set_detected_actions(session_id: uuid.UUID, actions: list[DetectedAction]) -> None:
    _actions[session_id] = actions


def get_detected_actions(session_id: uuid.UUID) -> list[DetectedAction]:
    return _actions.get(session_id, [])


def get_action(session_id: uuid.UUID, action_id: uuid.UUID) -> Optional[DetectedAction]:
    for action in _actions.get(session_id, []):
        if action.id == action_id:
            return action
    return None


def update_action_status(session_id: uuid.UUID, action_id: uuid.UUID, status: ActionStatus) -> None:
    for action in _actions.get(session_id, []):
        if action.id == action_id:
            action.status = status
            return


def add_flag(session_id: uuid.UUID, flag: FlaggedMoment) -> None:
    _flags.setdefault(session_id, []).append(flag)


def get_flags(session_id: uuid.UUID) -> list[FlaggedMoment]:
    return _flags.get(session_id, [])


def relabel_speakers(session_id: uuid.UUID, mapping: dict[str, str]) -> list[TranscriptSegment]:
    segments = _transcripts.get(session_id, [])
    for segment in segments:
        if segment.speaker in mapping:
            segment.speaker = mapping[segment.speaker]
    return segments


def set_segment_redacted(session_id: uuid.UUID, segment_id: uuid.UUID, redacted: bool) -> Optional[TranscriptSegment]:
    for segment in _transcripts.get(session_id, []):
        if segment.id == segment_id:
            segment.redacted = redacted
            return segment
    return None


def create_matter(matter: Matter) -> Matter:
    _matters[matter.id] = matter
    return matter


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
