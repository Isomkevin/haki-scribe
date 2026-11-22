"""In-memory hearing store (demo) + lifecycle helpers. Postgres via migration 003.

Lifecycle (enforced by `transition`):

  scheduled ─┬─> pending_confirm ──> matched ──> capturing ──> ingested ──> transcribed ──> reviewed ──> filed
             └─> rejected <─────────────┘  (re-match allowed from rejected)

A matter link is only ever set by a human confirm. Re-importing or
re-matching a hearing refreshes candidates but never undoes a confirmation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.models.schemas import (
    Hearing,
    HearingConfirmRequest,
    HearingCreate,
    HearingMatchCandidate,
    HearingStatus,
    Session,
    SessionSource,
)
from app.services import matter_resolution, storage

S = HearingStatus

ALLOWED_TRANSITIONS: dict[HearingStatus, frozenset[HearingStatus]] = {
    S.scheduled: frozenset({S.pending_confirm, S.matched, S.rejected}),
    S.pending_confirm: frozenset({S.pending_confirm, S.matched, S.rejected}),
    S.rejected: frozenset({S.pending_confirm, S.matched}),
    S.matched: frozenset({S.matched, S.capturing, S.ingested, S.rejected}),
    S.capturing: frozenset({S.ingested}),
    S.ingested: frozenset({S.transcribed}),
    S.transcribed: frozenset({S.transcribed, S.reviewed}),
    S.reviewed: frozenset({S.transcribed, S.filed}),
    S.filed: frozenset(),
}

# Before a session exists the matter link can still change.
_UNCOMMITTED = frozenset({S.scheduled, S.pending_confirm, S.rejected, S.matched})

_hearings: dict[UUID, Hearing] = {}
_candidates: dict[UUID, list[HearingMatchCandidate]] = {}
_confirmations: list[dict[str, Any]] = []


class InvalidTransition(ValueError):
    pass


def reset() -> None:
    _hearings.clear()
    _candidates.clear()
    _confirmations.clear()


def transition(hearing: Hearing, new_status: HearingStatus) -> Hearing:
    if new_status not in ALLOWED_TRANSITIONS[hearing.status]:
        raise InvalidTransition(f"Hearing cannot move from {hearing.status.value} to {new_status.value}")
    hearing.status = new_status
    hearing.updated_at = datetime.utcnow()
    return hearing


def list_hearings() -> list[Hearing]:
    return sorted(_hearings.values(), key=lambda h: h.starts_at or h.created_at, reverse=True)


def get_hearing(hearing_id: UUID) -> Optional[Hearing]:
    return _hearings.get(hearing_id)


def find_external(source: Any, external_id: str) -> Optional[Hearing]:
    for existing in _hearings.values():
        if existing.source == source and existing.external_id == external_id:
            return existing
    return None


def create_hearing(payload: HearingCreate) -> Hearing:
    hearing = Hearing(
        source=payload.source,
        external_id=payload.external_id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        court_name=payload.court_name,
        case_reference=payload.case_reference
        or matter_resolution.extract_case_reference(payload.title, payload.description),
        meeting_url=payload.meeting_url,
        platform_metadata=payload.platform_metadata or {},
        status=HearingStatus.scheduled,
    )
    _hearings[hearing.id] = hearing
    return hearing


def upsert_external(payload: HearingCreate) -> Hearing:
    existing = find_external(payload.source, payload.external_id) if payload.external_id else None
    if existing is None:
        return create_hearing(payload)
    existing.title = payload.title
    existing.description = payload.description
    existing.starts_at = payload.starts_at
    existing.ends_at = payload.ends_at
    existing.court_name = payload.court_name
    existing.case_reference = payload.case_reference or existing.case_reference
    existing.meeting_url = payload.meeting_url
    # Merge so pipeline / recording metadata survives a calendar re-import.
    existing.platform_metadata = {**(existing.platform_metadata or {}), **(payload.platform_metadata or {})}
    existing.updated_at = datetime.utcnow()
    return existing


def propose_matches(hearing_id: UUID) -> list[HearingMatchCandidate]:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    raw = matter_resolution.propose_matches(
        storage.list_matters(),
        title=hearing.title,
        description=hearing.description or "",
        case_reference=hearing.case_reference,
        starts_at=hearing.starts_at,
    )
    candidates = [
        HearingMatchCandidate(
            hearing_id=hearing_id,
            matter_id=UUID(row["matter_id"]),
            score=float(row["score"]),
            rationale=row["rationale"],
            requires_confirmation=bool(row["requires_confirmation"]),
        )
        for row in raw
    ]
    _candidates[hearing_id] = candidates
    # Only unconfirmed hearings move to pending_confirm; a confirmed or
    # rejected decision stands until a human changes it.
    if hearing.status in (S.scheduled, S.pending_confirm):
        transition(hearing, S.pending_confirm)
        hearing.match_confidence = float(raw[0]["score"]) if raw else 0.0
        hearing.matter_id = None
        hearing.platform_metadata = {
            **(hearing.platform_metadata or {}),
            "match": {
                "ambiguous": matter_resolution.is_ambiguous(raw),
                "suggested_matter_id": (matter_resolution.best_match(raw) or {}).get("matter_id"),
            },
        }
    hearing.updated_at = datetime.utcnow()
    return candidates


def list_candidates(hearing_id: UUID) -> list[HearingMatchCandidate]:
    return list(_candidates.get(hearing_id, []))


def list_confirmations(hearing_id: Optional[UUID] = None) -> list[dict[str, Any]]:
    if hearing_id is None:
        return list(_confirmations)
    return [c for c in _confirmations if c["hearing_id"] == str(hearing_id)]


def confirm_match(hearing_id: UUID, body: HearingConfirmRequest, *, actor: str = "workspace") -> Hearing:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    if hearing.status not in _UNCOMMITTED:
        raise InvalidTransition(
            f"Matter link is locked once capture has started (status {hearing.status.value})"
        )
    if body.decision not in ("confirm", "reject"):
        raise ValueError("decision must be 'confirm' or 'reject'")
    if body.decision == "reject":
        transition(hearing, S.rejected)
        hearing.matter_id = None
        hearing.match_confidence = None
        _confirmations.append(
            {
                "hearing_id": str(hearing_id),
                "matter_id": None,
                "decision": "reject",
                "actor_label": actor,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        return hearing

    if not body.matter_id:
        raise ValueError("matter_id required to confirm")
    matter = storage.get_matter(body.matter_id)
    if not matter:
        raise ValueError("matter_not_found")
    transition(hearing, S.matched)
    hearing.matter_id = body.matter_id
    for c in _candidates.get(hearing_id) or []:
        if c.matter_id == body.matter_id:
            hearing.match_confidence = c.score
            break
    _confirmations.append(
        {
            "hearing_id": str(hearing_id),
            "matter_id": str(body.matter_id),
            "decision": "confirm",
            "actor_label": actor,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    # A recording that arrived before the human confirmed is now usable.
    if hearing.recording_object_key:
        transition(hearing, S.ingested)
    return hearing


def attach_recording(hearing_id: UUID, *, object_key: str, meta: Optional[dict[str, Any]] = None) -> Hearing:
    """Attach a stored recording. Only advances to `ingested` once a matter is confirmed."""
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    if hearing.status in (S.transcribed, S.reviewed, S.filed):
        raise InvalidTransition(f"Hearing already {hearing.status.value}; create a new hearing for a new recording")
    hearing.recording_object_key = object_key
    hearing.platform_metadata = {**(hearing.platform_metadata or {}), "recording": meta or {}}
    if hearing.status in (S.matched, S.capturing):
        transition(hearing, S.ingested)
    hearing.updated_at = datetime.utcnow()
    return hearing


def create_session_from_hearing(hearing_id: UUID) -> dict[str, Any]:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    if hearing.matter_id is None:
        raise ValueError("Confirm a matter match before creating a session")
    if hearing.session_id:
        existing = storage.get_session(hearing.session_id)
        if existing is not None:
            return {"hearing": hearing, "session": existing}
    session = storage.create_session(
        Session(
            title=hearing.title,
            source=SessionSource.mic,
            language_hint=None,
        )
    )
    storage.link_matter_to_session(session.id, hearing.matter_id)
    hearing.session_id = session.id
    if hearing.status == S.matched:
        transition(hearing, S.capturing)
    hearing.updated_at = datetime.utcnow()
    return {"hearing": hearing, "session": session}


def set_pipeline_state(hearing_id: UUID, **fields: Any) -> Hearing:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    pipeline = dict((hearing.platform_metadata or {}).get("pipeline") or {})
    pipeline.update(fields)
    pipeline["updated_at"] = datetime.utcnow().isoformat()
    hearing.platform_metadata = {**(hearing.platform_metadata or {}), "pipeline": pipeline}
    hearing.updated_at = datetime.utcnow()
    return hearing


def mark_reviewed(hearing_id: UUID, *, actor: str = "workspace") -> Hearing:
    """Human sign-off that the transcript and extracted record are correct."""
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    transition(hearing, S.reviewed)
    hearing.platform_metadata = {
        **(hearing.platform_metadata or {}),
        "review": {"actor_label": actor, "reviewed_at": datetime.utcnow().isoformat()},
    }
    return hearing


def pending_confirmations() -> list[Hearing]:
    return [h for h in _hearings.values() if h.status == HearingStatus.pending_confirm]
