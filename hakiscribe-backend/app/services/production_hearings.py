"""Org-scoped hearings repository over migration 003 (ADR-012 b).

Uses the Supabase service client after membership has been verified by
tenant_context. Demo mode continues to use app.services.hearings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.models.schemas import (
    Hearing,
    HearingConfirmRequest,
    HearingCreate,
    HearingMatchCandidate,
    HearingStatus,
    Session,
    SessionSource,
    SessionStatus,
)
from app.services import matter_resolution
from app.services.hearings import ALLOWED_TRANSITIONS, InvalidTransition


def _row_to_hearing(row: dict[str, Any]) -> Hearing:
    return Hearing(
        id=UUID(str(row["id"])),
        source=row["source"],
        external_id=row.get("external_id"),
        title=row["title"],
        description=row.get("description"),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        court_name=row.get("court_name"),
        case_reference=row.get("case_reference"),
        meeting_url=row.get("meeting_url"),
        platform_metadata=row.get("platform_metadata") or {},
        status=row["status"],
        matter_id=UUID(str(row["matter_id"])) if row.get("matter_id") else None,
        session_id=UUID(str(row["session_id"])) if row.get("session_id") else None,
        match_confidence=row.get("match_confidence"),
        recording_object_key=row.get("recording_object_key"),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _hearing_to_row(hearing: Hearing, organisation_id: UUID) -> dict[str, Any]:
    return {
        "id": str(hearing.id),
        "organisation_id": str(organisation_id),
        "source": hearing.source.value if hasattr(hearing.source, "value") else hearing.source,
        "external_id": hearing.external_id,
        "title": hearing.title,
        "description": hearing.description,
        "starts_at": hearing.starts_at.isoformat() if hearing.starts_at else None,
        "ends_at": hearing.ends_at.isoformat() if hearing.ends_at else None,
        "court_name": hearing.court_name,
        "case_reference": hearing.case_reference,
        "meeting_url": hearing.meeting_url,
        "platform_metadata": hearing.platform_metadata or {},
        "status": hearing.status.value if hasattr(hearing.status, "value") else hearing.status,
        "matter_id": str(hearing.matter_id) if hearing.matter_id else None,
        "session_id": str(hearing.session_id) if hearing.session_id else None,
        "match_confidence": hearing.match_confidence,
        "recording_object_key": hearing.recording_object_key,
        "updated_at": datetime.utcnow().isoformat(),
    }


class ProductionHearingsRepo:
    def __init__(self, client: Any, organisation_id: UUID):
        self.client = client
        self.organisation_id = organisation_id

    def list_hearings(self) -> list[Hearing]:
        result = (
            self.client.table("haki_hearings")
            .select("*")
            .eq("organisation_id", str(self.organisation_id))
            .order("starts_at", desc=True)
            .execute()
        )
        return [_row_to_hearing(row) for row in (result.data or [])]

    def get_hearing(self, hearing_id: UUID) -> Hearing:
        result = (
            self.client.table("haki_hearings")
            .select("*")
            .eq("id", str(hearing_id))
            .eq("organisation_id", str(self.organisation_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Hearing not found")
        return _row_to_hearing(result.data[0])

    def find_external(self, source: str, external_id: str) -> Optional[Hearing]:
        result = (
            self.client.table("haki_hearings")
            .select("*")
            .eq("organisation_id", str(self.organisation_id))
            .eq("source", source)
            .eq("external_id", external_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return _row_to_hearing(result.data[0])

    def upsert(self, hearing: Hearing) -> Hearing:
        row = _hearing_to_row(hearing, self.organisation_id)
        result = self.client.table("haki_hearings").upsert(row).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Could not save hearing")
        return _row_to_hearing(result.data[0])

    def create(self, payload: HearingCreate) -> Hearing:
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
        return self.upsert(hearing)

    def upsert_external(self, payload: HearingCreate) -> Hearing:
        source = payload.source.value if hasattr(payload.source, "value") else str(payload.source)
        existing = self.find_external(source, payload.external_id) if payload.external_id else None
        if existing is None:
            return self.create(payload)
        existing.title = payload.title
        existing.description = payload.description
        existing.starts_at = payload.starts_at
        existing.ends_at = payload.ends_at
        existing.court_name = payload.court_name
        existing.case_reference = payload.case_reference or existing.case_reference
        existing.meeting_url = payload.meeting_url
        existing.platform_metadata = {**(existing.platform_metadata or {}), **(payload.platform_metadata or {})}
        existing.updated_at = datetime.utcnow()
        return self.upsert(existing)

    def transition(self, hearing: Hearing, new_status: HearingStatus) -> Hearing:
        if new_status not in ALLOWED_TRANSITIONS[hearing.status]:
            raise InvalidTransition(f"Hearing cannot move from {hearing.status.value} to {new_status.value}")
        hearing.status = new_status
        hearing.updated_at = datetime.utcnow()
        return self.upsert(hearing)

    def list_org_matters(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("haki_matters")
            .select("id, client_name, matter_name")
            .eq("organisation_id", str(self.organisation_id))
            .execute()
        )
        return list(result.data or [])

    def propose_matches(self, hearing_id: UUID) -> list[HearingMatchCandidate]:
        from app.models.schemas import Matter

        hearing = self.get_hearing(hearing_id)
        matters = [
            Matter(id=UUID(str(m["id"])), client_name=m["client_name"], matter_name=m["matter_name"])
            for m in self.list_org_matters()
        ]
        raw = matter_resolution.propose_matches(
            matters,
            title=hearing.title,
            description=hearing.description or "",
            case_reference=hearing.case_reference,
            starts_at=hearing.starts_at,
        )
        # Replace candidates for this hearing
        self.client.table("haki_hearing_match_candidates").delete().eq("hearing_id", str(hearing_id)).execute()
        candidates: list[HearingMatchCandidate] = []
        for row in raw:
            cand = HearingMatchCandidate(
                hearing_id=hearing_id,
                matter_id=UUID(row["matter_id"]),
                score=float(row["score"]),
                rationale=row.get("rationale"),
                requires_confirmation=bool(row.get("requires_confirmation")),
            )
            self.client.table("haki_hearing_match_candidates").insert(
                {
                    "hearing_id": str(hearing_id),
                    "matter_id": str(cand.matter_id),
                    "score": cand.score,
                    "rationale": cand.rationale,
                }
            ).execute()
            candidates.append(cand)
        if hearing.status in (HearingStatus.scheduled, HearingStatus.pending_confirm):
            hearing = self.transition(hearing, HearingStatus.pending_confirm)
            hearing.match_confidence = float(raw[0]["score"]) if raw else 0.0
            hearing.matter_id = None
            hearing.platform_metadata = {
                **(hearing.platform_metadata or {}),
                "match": {
                    "ambiguous": matter_resolution.is_ambiguous(raw),
                    "suggested_matter_id": (matter_resolution.best_match(raw) or {}).get("matter_id"),
                },
            }
            hearing = self.upsert(hearing)
        return candidates

    def list_candidates(self, hearing_id: UUID) -> list[HearingMatchCandidate]:
        self.get_hearing(hearing_id)  # org check
        result = (
            self.client.table("haki_hearing_match_candidates")
            .select("*")
            .eq("hearing_id", str(hearing_id))
            .order("score", desc=True)
            .execute()
        )
        return [
            HearingMatchCandidate(
                id=UUID(str(row["id"])) if row.get("id") else uuid4(),
                hearing_id=hearing_id,
                matter_id=UUID(str(row["matter_id"])),
                score=float(row["score"]),
                rationale=row.get("rationale"),
                requires_confirmation=float(row["score"]) < 0.85,
            )
            for row in (result.data or [])
        ]

    def confirm_match(self, hearing_id: UUID, body: HearingConfirmRequest, *, actor: str) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        locked = {
            HearingStatus.capturing,
            HearingStatus.ingested,
            HearingStatus.transcribed,
            HearingStatus.reviewed,
            HearingStatus.filed,
        }
        if hearing.status in locked:
            raise InvalidTransition(f"Matter link is locked (status {hearing.status.value})")
        if body.decision == "reject":
            hearing = self.transition(hearing, HearingStatus.rejected)
            hearing.matter_id = None
            hearing.match_confidence = None
            hearing = self.upsert(hearing)
            self._audit(hearing_id, None, "reject", actor)
            return hearing
        if not body.matter_id:
            raise ValueError("matter_id required to confirm")
        matter = (
            self.client.table("haki_matters")
            .select("id")
            .eq("id", str(body.matter_id))
            .eq("organisation_id", str(self.organisation_id))
            .limit(1)
            .execute()
        )
        if not matter.data:
            raise ValueError("matter_not_found")
        hearing = self.transition(hearing, HearingStatus.matched)
        hearing.matter_id = body.matter_id
        for c in self.list_candidates(hearing_id):
            if c.matter_id == body.matter_id:
                hearing.match_confidence = c.score
                break
        hearing = self.upsert(hearing)
        self._audit(hearing_id, body.matter_id, "confirm", actor)
        if hearing.recording_object_key:
            hearing = self.transition(hearing, HearingStatus.ingested)
        return hearing

    def _audit(self, hearing_id: UUID, matter_id: Optional[UUID], decision: str, actor: str) -> None:
        self.client.table("haki_hearing_confirmations").insert(
            {
                "hearing_id": str(hearing_id),
                "matter_id": str(matter_id) if matter_id else None,
                "decision": decision,
                "actor_label": actor,
            }
        ).execute()

    def set_pipeline_state(self, hearing_id: UUID, **fields: Any) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        pipeline = dict((hearing.platform_metadata or {}).get("pipeline") or {})
        pipeline.update(fields)
        pipeline["updated_at"] = datetime.utcnow().isoformat()
        hearing.platform_metadata = {**(hearing.platform_metadata or {}), "pipeline": pipeline}
        hearing.updated_at = datetime.utcnow()
        return self.upsert(hearing)

    def attach_recording(self, hearing_id: UUID, *, object_key: str, meta: Optional[dict[str, Any]] = None) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        if hearing.status in (HearingStatus.transcribed, HearingStatus.reviewed, HearingStatus.filed):
            raise InvalidTransition(f"Hearing already {hearing.status.value}")
        hearing.recording_object_key = object_key
        hearing.platform_metadata = {**(hearing.platform_metadata or {}), "recording": meta or {}}
        if hearing.status in (HearingStatus.matched, HearingStatus.capturing):
            hearing = self.transition(hearing, HearingStatus.ingested)
        else:
            hearing = self.upsert(hearing)
        return hearing

    def mark_reviewed(self, hearing_id: UUID, *, actor: str) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        hearing = self.transition(hearing, HearingStatus.reviewed)
        hearing.platform_metadata = {
            **(hearing.platform_metadata or {}),
            "review": {"actor_label": actor, "reviewed_at": datetime.utcnow().isoformat()},
        }
        return self.upsert(hearing)

    def pending_confirmations(self) -> list[Hearing]:
        return [h for h in self.list_hearings() if h.status == HearingStatus.pending_confirm]

    def create_session_from_hearing(
        self,
        hearing_id: UUID,
        *,
        workspace_id: UUID,
        user_id: str,
    ) -> dict[str, Any]:
        hearing = self.get_hearing(hearing_id)
        if hearing.matter_id is None:
            raise ValueError("Confirm a matter match before creating a session")
        if hearing.session_id:
            existing = (
                self.client.table("haki_sessions")
                .select("*")
                .eq("id", str(hearing.session_id))
                .eq("organisation_id", str(self.organisation_id))
                .limit(1)
                .execute()
            )
            if existing.data:
                row = existing.data[0]
                session = Session(
                    id=UUID(str(row["id"])),
                    title=row["title"],
                    source=row.get("source") or SessionSource.mic,
                    language_hint=row.get("language_hint"),
                    status=row.get("status") or SessionStatus.recording,
                    created_at=row.get("created_at") or datetime.utcnow(),
                    updated_at=row.get("updated_at") or datetime.utcnow(),
                )
                return {"hearing": hearing, "session": session}

        session = Session(title=hearing.title, source=SessionSource.mic, language_hint=None)
        inserted = (
            self.client.table("haki_sessions")
            .insert(
                {
                    "id": str(session.id),
                    "organisation_id": str(self.organisation_id),
                    "workspace_id": str(workspace_id),
                    "created_by": user_id,
                    "title": session.title,
                    "source": session.source.value,
                    "status": session.status.value,
                    "language_hint": session.language_hint,
                    "matter_id": str(hearing.matter_id),
                }
            )
            .execute()
        )
        if not inserted.data:
            raise HTTPException(status_code=500, detail="Could not create hearing session")
        hearing.session_id = session.id
        if hearing.status == HearingStatus.matched:
            hearing = self.transition(hearing, HearingStatus.capturing)
        else:
            hearing = self.upsert(hearing)
        return {"hearing": hearing, "session": session}

    def write_transcript_segments(self, session_id: UUID, segments: list[Any], *, user_id: str) -> None:
        # Replace, not append: re-processing or a retried job must not duplicate the transcript.
        self.client.table("haki_session_records").delete().eq("session_id", str(session_id)).eq(
            "record_type", "segment"
        ).execute()
        rows = [
            {
                "session_id": str(session_id),
                "record_type": "segment",
                "payload": seg.model_dump(mode="json") if hasattr(seg, "model_dump") else seg,
                "created_by": user_id,
            }
            for seg in segments
        ]
        # Batched: a three-hour hearing has thousands of segments.
        for start in range(0, len(rows), 500):
            self.client.table("haki_session_records").insert(rows[start : start + 500]).execute()

    def mark_session_ready(self, session_id: UUID) -> None:
        self.client.table("haki_sessions").update({"status": SessionStatus.ready.value}).eq(
            "id", str(session_id)
        ).execute()

    def start_capture(self, hearing_id: UUID, *, meta: Optional[dict[str, Any]] = None) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        if hearing.matter_id is None:
            raise ValueError("Confirm the matter link before starting capture")
        if hearing.status not in (HearingStatus.matched, HearingStatus.capturing):
            raise InvalidTransition(f"Cannot start capture from {hearing.status.value}")
        if hearing.status == HearingStatus.matched:
            hearing = self.transition(hearing, HearingStatus.capturing)
        hearing.platform_metadata = {
            **(hearing.platform_metadata or {}),
            "capture": {**(meta or {}), "started_at": datetime.utcnow().isoformat(), "state": "active"},
        }
        return self.upsert(hearing)

    def stop_capture(self, hearing_id: UUID, *, object_key: Optional[str] = None, meta: Optional[dict[str, Any]] = None) -> Hearing:
        hearing = self.get_hearing(hearing_id)
        if hearing.status != HearingStatus.capturing:
            raise InvalidTransition(f"Hearing is not capturing (status {hearing.status.value})")
        capture = dict((hearing.platform_metadata or {}).get("capture") or {})
        capture.update(meta or {})
        capture["state"] = "stopped"
        capture["stopped_at"] = datetime.utcnow().isoformat()
        hearing.platform_metadata = {**(hearing.platform_metadata or {}), "capture": capture}
        if object_key:
            return self.attach_recording(hearing_id, object_key=object_key, meta=meta)
        hearing = self.upsert(hearing)
        return hearing


def resolve_zoom_organisation(host_id: Optional[str], account_id: Optional[str] = None) -> Optional[UUID]:
    """Map Zoom host/account id → organisation via ZOOM_HOST_ORG_MAP JSON env."""
    import json
    import os

    raw = os.environ.get("ZOOM_HOST_ORG_MAP") or "{}"
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        mapping = {}
    if not isinstance(mapping, dict):
        return None
    for key in (host_id, account_id):
        if key and key in mapping:
            try:
                return UUID(str(mapping[key]))
            except ValueError:
                continue
    default = os.environ.get("ZOOM_DEFAULT_ORGANISATION_ID")
    if default:
        try:
            return UUID(default)
        except ValueError:
            return None
    return None
