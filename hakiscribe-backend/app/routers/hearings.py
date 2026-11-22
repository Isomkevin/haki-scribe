"""Virtual court hearings API — import, match, confirm, session, upload."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource
from app.services import hearings as hearings_service
from app.services.court_adapters import GoogleCalendarAdapter, TeamsGraphAdapter, ZoomAdapter

router = APIRouter()


class ManualHearingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    court_name: Optional[str] = None
    case_reference: Optional[str] = None
    meeting_url: Optional[str] = None


@router.get("")
def list_hearings():
    return [h.model_dump(mode="json") for h in hearings_service.list_hearings()]


@router.get("/pending-confirm")
def pending_confirm():
    return [h.model_dump(mode="json") for h in hearings_service.pending_confirmations()]


@router.get("/adapters")
def adapter_status():
    adapters = [GoogleCalendarAdapter(), TeamsGraphAdapter(), ZoomAdapter()]
    return [
        {
            "source": a.source,
            "configured": a.configured(),
            "capabilities": a.capability_notes(),
        }
        for a in adapters
    ]


@router.get("/{hearing_id}")
def get_hearing(hearing_id: UUID):
    hearing = hearings_service.get_hearing(hearing_id)
    if not hearing:
        raise HTTPException(status_code=404, detail="Hearing not found")
    return {
        "hearing": hearing.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in hearings_service.list_candidates(hearing_id)],
    }


@router.post("/import/manual")
def import_manual(body: ManualHearingRequest):
    from datetime import datetime

    def parse(v: Optional[str]):
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    hearing = hearings_service.create_hearing(
        HearingCreate(
            source=HearingSource.manual_upload,
            title=body.title,
            description=body.description,
            starts_at=parse(body.starts_at),
            ends_at=parse(body.ends_at),
            court_name=body.court_name,
            case_reference=body.case_reference,
            meeting_url=body.meeting_url,
        )
    )
    candidates = hearings_service.propose_matches(hearing.id)
    return {
        "hearing": hearing.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in candidates],
    }


@router.post("/import/calendar")
async def import_calendar(days: int = Query(14, ge=1, le=60)):
    adapter = GoogleCalendarAdapter()
    if not adapter.configured():
        raise HTTPException(status_code=400, detail="Google Calendar is not connected")
    events = await adapter.list_upcoming(days=days)
    imported = []
    for ev in events:
        hearing = hearings_service.upsert_external(
            HearingCreate(
                source=HearingSource.google_calendar,
                external_id=ev.external_id,
                title=ev.title,
                description=ev.description,
                starts_at=ev.starts_at,
                ends_at=ev.ends_at,
                meeting_url=ev.meeting_url,
                court_name=ev.court_name,
                case_reference=ev.case_reference,
                platform_metadata=ev.metadata,
            )
        )
        candidates = hearings_service.propose_matches(hearing.id)
        imported.append(
            {
                "hearing": hearing.model_dump(mode="json"),
                "candidates": [c.model_dump(mode="json") for c in candidates],
            }
        )
    return {"imported": len(imported), "items": imported}


@router.post("/import/teams")
async def import_teams(days: int = Query(14, ge=1, le=60)):
    adapter = TeamsGraphAdapter()
    if not adapter.configured():
        raise HTTPException(
            status_code=400,
            detail="Microsoft Teams Graph is not connected. Connect teams_graph or OneDrive Microsoft OAuth.",
        )
    events = await adapter.list_upcoming(days=days)
    return _import_events(HearingSource.teams_graph, events)


@router.post("/import/zoom")
async def import_zoom(days: int = Query(14, ge=1, le=60)):
    adapter = ZoomAdapter()
    if not adapter.configured():
        raise HTTPException(status_code=400, detail="Zoom is not connected")
    events = await adapter.list_upcoming(days=days)
    return _import_events(HearingSource.zoom, events)


def _import_events(source: HearingSource, events) -> dict[str, Any]:
    imported = []
    for ev in events:
        hearing = hearings_service.upsert_external(
            HearingCreate(
                source=source,
                external_id=ev.external_id,
                title=ev.title,
                description=ev.description,
                starts_at=ev.starts_at,
                ends_at=ev.ends_at,
                meeting_url=ev.meeting_url,
                court_name=ev.court_name,
                case_reference=ev.case_reference,
                platform_metadata=ev.metadata,
            )
        )
        candidates = hearings_service.propose_matches(hearing.id)
        imported.append(
            {
                "hearing": hearing.model_dump(mode="json"),
                "candidates": [c.model_dump(mode="json") for c in candidates],
            }
        )
    return {"imported": len(imported), "items": imported}


@router.post("/{hearing_id}/match")
def match_hearing(hearing_id: UUID):
    try:
        candidates = hearings_service.propose_matches(hearing_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Hearing not found") from None
    hearing = hearings_service.get_hearing(hearing_id)
    return {
        "hearing": hearing.model_dump(mode="json") if hearing else None,
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "requires_human_confirmation": True,
    }


@router.post("/{hearing_id}/confirm")
def confirm_hearing(hearing_id: UUID, body: HearingConfirmRequest):
    try:
        hearing = hearings_service.confirm_match(hearing_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="Hearing not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return hearing.model_dump(mode="json")


@router.post("/{hearing_id}/session")
def create_session(hearing_id: UUID):
    try:
        result = hearings_service.create_session_from_hearing(hearing_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Hearing not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "hearing": result["hearing"].model_dump(mode="json"),
        "session": result["session"].model_dump(mode="json"),
    }


@router.post("/{hearing_id}/upload")
async def upload_recording(hearing_id: UUID, file: UploadFile = File(...)):
    hearing = hearings_service.get_hearing(hearing_id)
    if not hearing:
        raise HTTPException(status_code=404, detail="Hearing not found")
    raw = await file.read()
    # Demo: store metadata key only (object store optional). Stage B persists bytes to S3/volume.
    key = f"hearings/{hearing_id}/{file.filename or 'recording.bin'}"
    try:
        from app.services import object_store

        if hasattr(object_store, "put_bytes"):
            object_store.put_bytes(key, raw, content_type=file.content_type or "application/octet-stream")
    except Exception:  # noqa: BLE001
        pass
    updated = hearings_service.attach_recording(
        hearing_id,
        object_key=key,
        meta={"filename": file.filename, "bytes": len(raw), "content_type": file.content_type},
    )
    return updated.model_dump(mode="json")
