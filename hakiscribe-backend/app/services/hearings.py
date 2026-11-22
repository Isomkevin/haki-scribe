"""In-memory hearing store (demo) + lifecycle helpers. Postgres via migration 003."""

from __future__ import annotations

import uuid
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

_hearings: dict[UUID, Hearing] = {}
_candidates: dict[UUID, list[HearingMatchCandidate]] = {}
_confirmations: list[dict[str, Any]] = []


def reset() -> None:
    _hearings.clear()
    _candidates.clear()
    _confirmations.clear()


def list_hearings() -> list[Hearing]:
    return sorted(_hearings.values(), key=lambda h: h.starts_at or h.created_at, reverse=True)


def get_hearing(hearing_id: UUID) -> Optional[Hearing]:
    return _hearings.get(hearing_id)


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
    if payload.external_id:
        for existing in _hearings.values():
            if existing.source == payload.source and existing.external_id == payload.external_id:
                existing.title = payload.title
                existing.description = payload.description
                existing.starts_at = payload.starts_at
                existing.ends_at = payload.ends_at
                existing.court_name = payload.court_name
                existing.case_reference = payload.case_reference or existing.case_reference
                existing.meeting_url = payload.meeting_url
                existing.platform_metadata = payload.platform_metadata or existing.platform_metadata
                existing.updated_at = datetime.utcnow()
                return existing
    return create_hearing(payload)


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
    top = matter_resolution.best_match(raw)
    if top is None:
        hearing.status = HearingStatus.pending_confirm
        hearing.match_confidence = float(raw[0]["score"]) if raw else 0.0
        hearing.matter_id = None
    else:
        hearing.status = HearingStatus.pending_confirm if True else HearingStatus.matched
        # Even high confidence requires explicit confirm in Stage A (safe default).
        hearing.match_confidence = float(top["score"])
        hearing.matter_id = None
    hearing.updated_at = datetime.utcnow()
    return candidates


def list_candidates(hearing_id: UUID) -> list[HearingMatchCandidate]:
    return list(_candidates.get(hearing_id, []))


def confirm_match(hearing_id: UUID, body: HearingConfirmRequest, *, actor: str = "workspace") -> Hearing:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    if body.decision == "reject":
        hearing.status = HearingStatus.rejected
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
        hearing.updated_at = datetime.utcnow()
        return hearing

    if not body.matter_id:
        raise ValueError("matter_id required to confirm")
    matter = storage.get_matter(body.matter_id)
    if not matter:
        raise ValueError("matter_not_found")
    hearing.matter_id = body.matter_id
    hearing.status = HearingStatus.matched
    cands = _candidates.get(hearing_id) or []
    for c in cands:
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
    hearing.updated_at = datetime.utcnow()
    return hearing


def attach_recording(hearing_id: UUID, *, object_key: str, meta: Optional[dict[str, Any]] = None) -> Hearing:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    hearing.recording_object_key = object_key
    hearing.platform_metadata = {**(hearing.platform_metadata or {}), "recording": meta or {}}
    hearing.status = HearingStatus.ingested
    hearing.updated_at = datetime.utcnow()
    return hearing


def create_session_from_hearing(hearing_id: UUID) -> dict[str, Any]:
    hearing = _hearings.get(hearing_id)
    if not hearing:
        raise KeyError("hearing_not_found")
    if hearing.status not in (HearingStatus.matched, HearingStatus.ingested, HearingStatus.transcribed):
        if hearing.matter_id is None:
            raise ValueError("Confirm a matter match before creating a session")
    session = storage.create_session(
        Session(
            title=hearing.title,
            source=SessionSource.mic,
            language_hint=None,
        )
    )
    if hearing.matter_id:
        storage.link_matter_to_session(session.id, hearing.matter_id)
    hearing.session_id = session.id
    hearing.status = HearingStatus.capturing if hearing.status == HearingStatus.matched else hearing.status
    hearing.updated_at = datetime.utcnow()
    return {"hearing": hearing, "session": session}


def pending_confirmations() -> list[Hearing]:
    return [h for h in _hearings.values() if h.status == HearingStatus.pending_confirm]
