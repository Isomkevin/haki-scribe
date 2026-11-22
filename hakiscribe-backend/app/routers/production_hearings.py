"""Org-scoped hearings API under /production/hearings (ADR-012 b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource
from app.services import hearing_pipeline, recording_store
from app.services.court_adapters import AdapterError, GoogleCalendarAdapter, TeamsGraphAdapter, ZoomAdapter
from app.services.hearings import InvalidTransition
from app.services.production_auth import require_csrf
from app.services.production_hearings import ProductionHearingsRepo
from app.services.tenant_context import production_client, require_organisation, require_workspace

router = APIRouter()


class ManualHearingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    court_name: Optional[str] = None
    case_reference: Optional[str] = None
    meeting_url: Optional[str] = None


def _repo(organisation_id: UUID) -> ProductionHearingsRepo:
    return ProductionHearingsRepo(production_client(), organisation_id)


def _parse_dt(v: Optional[str]):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


@router.get("")
async def list_hearings(context=Depends(require_organisation)):
    _, organisation_id = context
    return [h.model_dump(mode="json") for h in _repo(organisation_id).list_hearings()]


@router.get("/pending-confirm")
async def pending_confirm(context=Depends(require_organisation)):
    _, organisation_id = context
    return [h.model_dump(mode="json") for h in _repo(organisation_id).pending_confirmations()]


@router.get("/adapters")
async def adapter_status(context=Depends(require_organisation)):
    _ = context
    from app.services.court_adapters import teams_bot, zoom_bot

    adapters = [GoogleCalendarAdapter(), TeamsGraphAdapter(), ZoomAdapter(), teams_bot.TeamsCallingBot(), zoom_bot.ZoomMeetingBot()]
    return [
        {
            "source": a.source,
            "configured": a.configured(),
            "capabilities": a.capability_notes(),
        }
        for a in adapters
    ]


@router.get("/{hearing_id}")
async def get_hearing(hearing_id: UUID, context=Depends(require_organisation)):
    _, organisation_id = context
    repo = _repo(organisation_id)
    hearing = repo.get_hearing(hearing_id)
    return {
        "hearing": hearing.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in repo.list_candidates(hearing_id)],
    }


@router.post("/import/manual")
async def import_manual(
    body: ManualHearingRequest,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    repo = _repo(organisation_id)
    hearing = repo.create(
        HearingCreate(
            source=HearingSource.manual_upload,
            title=body.title,
            description=body.description,
            starts_at=_parse_dt(body.starts_at),
            ends_at=_parse_dt(body.ends_at),
            court_name=body.court_name,
            case_reference=body.case_reference,
            meeting_url=body.meeting_url,
        )
    )
    candidates = repo.propose_matches(hearing.id)
    return {
        "hearing": hearing.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in candidates],
    }


def _import_events(repo: ProductionHearingsRepo, source: HearingSource, events) -> dict[str, Any]:
    imported = []
    for ev in events:
        hearing = repo.upsert_external(
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
        candidates = repo.propose_matches(hearing.id)
        imported.append(
            {
                "hearing": hearing.model_dump(mode="json"),
                "candidates": [c.model_dump(mode="json") for c in candidates],
            }
        )
    return {"imported": len(imported), "items": imported}


@router.post("/import/calendar")
async def import_calendar(
    days: int = Query(14, ge=1, le=60),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    adapter = GoogleCalendarAdapter()
    if not adapter.configured():
        raise HTTPException(status_code=400, detail="Google Calendar is not connected")
    return _import_events(_repo(organisation_id), HearingSource.google_calendar, await adapter.list_upcoming(days=days))


@router.post("/import/teams")
async def import_teams(
    days: int = Query(14, ge=1, le=60),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    adapter = TeamsGraphAdapter()
    if not adapter.configured():
        raise HTTPException(
            status_code=400,
            detail="Microsoft Teams Graph is not connected. Connect teams_graph or OneDrive Microsoft OAuth.",
        )
    return _import_events(_repo(organisation_id), HearingSource.teams_graph, await adapter.list_upcoming(days=days))


@router.post("/import/zoom")
async def import_zoom(
    days: int = Query(14, ge=1, le=60),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    adapter = ZoomAdapter()
    if not adapter.configured():
        raise HTTPException(status_code=400, detail="Zoom is not connected")
    return _import_events(_repo(organisation_id), HearingSource.zoom, await adapter.list_upcoming(days=days))


@router.post("/{hearing_id}/match")
async def match_hearing(hearing_id: UUID, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    _, organisation_id = context
    repo = _repo(organisation_id)
    candidates = repo.propose_matches(hearing_id)
    hearing = repo.get_hearing(hearing_id)
    return {
        "hearing": hearing.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "requires_human_confirmation": True,
    }


@router.post("/{hearing_id}/confirm")
async def confirm_hearing(
    hearing_id: UUID,
    body: HearingConfirmRequest,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    repo = _repo(organisation_id)
    try:
        hearing = repo.confirm_match(hearing_id, body, actor=user.email or user.id)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return hearing.model_dump(mode="json")


@router.post("/{hearing_id}/session")
async def create_session(
    hearing_id: UUID,
    context=Depends(require_workspace),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id, workspace_id = context
    repo = _repo(organisation_id)
    try:
        result = repo.create_session_from_hearing(hearing_id, workspace_id=workspace_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "hearing": result["hearing"].model_dump(mode="json"),
        "session": result["session"].model_dump(mode="json"),
    }


def _ingest_error(exc: Exception) -> HTTPException:
    if isinstance(exc, recording_store.RecordingTooLarge):
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, InvalidTransition):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/{hearing_id}/upload")
async def upload_recording(
    hearing_id: UUID,
    file: UploadFile = File(...),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    repo = _repo(organisation_id)
    repo.get_hearing(hearing_id)
    raw = await file.read()
    try:
        updated = hearing_pipeline.ingest_recording(hearing_id, file.filename, raw, file.content_type, store=repo)
    except (ValueError, InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return updated.model_dump(mode="json")


@router.post("/{hearing_id}/transcript")
async def upload_transcript(
    hearing_id: UUID,
    file: UploadFile = File(...),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    repo = _repo(organisation_id)
    repo.get_hearing(hearing_id)
    raw = await file.read()
    try:
        updated = hearing_pipeline.ingest_transcript(
            hearing_id, raw.decode("utf-8", errors="replace"), origin="upload", store=repo
        )
    except (ValueError, InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return updated.model_dump(mode="json")


_FETCH_ADAPTERS = {"zoom": ZoomAdapter, "teams_graph": TeamsGraphAdapter}


@router.post("/{hearing_id}/fetch-recording")
async def fetch_recording(
    hearing_id: UUID,
    prefer: str = Query("audio", pattern="^(audio|transcript)$"),
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    repo = _repo(organisation_id)
    hearing = repo.get_hearing(hearing_id)
    adapter_cls = _FETCH_ADAPTERS.get(hearing.source.value)
    if adapter_cls is None:
        raise HTTPException(status_code=400, detail=f"{hearing.source.value} hearings have no platform recording API")
    adapter = adapter_cls()
    if not adapter.configured():
        raise HTTPException(status_code=400, detail=f"{hearing.source.value} is not connected")
    try:
        artifact = await adapter.fetch_artifact(hearing, prefer=prefer)
    except AdapterError as exc:
        raise HTTPException(status_code=502 if (exc.status or 0) >= 500 else 400, detail=str(exc)) from exc
    try:
        if artifact.kind == "transcript":
            updated = hearing_pipeline.ingest_transcript(
                hearing_id, artifact.data.decode("utf-8", errors="replace"), origin=hearing.source.value, store=repo
            )
        else:
            updated = hearing_pipeline.ingest_recording(
                hearing_id, artifact.filename, artifact.data, artifact.content_type, store=repo
            )
    except (ValueError, InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return {"hearing": updated.model_dump(mode="json"), "artifact": {"kind": artifact.kind, **artifact.metadata}}


async def _process_in_background(hearing_id: UUID, organisation_id: UUID, workspace_id: UUID, user_id: str, **kwargs: Any) -> None:
    try:
        repo = _repo(organisation_id)
        await hearing_pipeline.process_hearing(
            hearing_id,
            store=repo,
            create_session_kwargs={"workspace_id": workspace_id, "user_id": user_id},
            **kwargs,
        )
    except Exception:  # noqa: BLE001
        pass


@router.post("/{hearing_id}/process")
async def process_hearing(
    hearing_id: UUID,
    background_tasks: BackgroundTasks,
    wait: bool = Query(False),
    use_llm: bool = Query(True),
    diarize: bool = Query(False),
    language_hint: Optional[str] = Query(None),
    context=Depends(require_workspace),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id, workspace_id = context
    repo = _repo(organisation_id)
    hearing = repo.get_hearing(hearing_id)
    kwargs = {"use_llm": use_llm, "diarize": diarize, "language_hint": language_hint}
    session_kwargs = {"workspace_id": workspace_id, "user_id": user.id}
    if not wait:
        if hearing.matter_id is None:
            raise HTTPException(status_code=409, detail="Confirm the matter link before processing this hearing")
        from app.services import ai_mode, trigger_client

        repo.set_pipeline_state(hearing_id, state="queued", step="queued", error=None)
        run_id = None
        if not ai_mode.prefer_in_process_jobs():
            run_id = await trigger_client.trigger_enqueue(
                "process-hearing",
                {
                    "hearing_id": str(hearing_id),
                    "organisation_id": str(organisation_id),
                    "workspace_id": str(workspace_id),
                    "user_id": user.id,
                    **kwargs,
                },
            )
        if run_id:
            repo.set_pipeline_state(hearing_id, job_id=run_id, run_id=run_id, queue="trigger")
            return {"status": "queued", "run_id": run_id, "hearing": hearing.model_dump(mode="json")}
        background_tasks.add_task(
            _process_in_background, hearing_id, organisation_id, workspace_id, user.id, **kwargs
        )
        return {"status": "queued", "hearing": hearing.model_dump(mode="json")}

    from app.services import ai_mode

    try:
        result = await hearing_pipeline.process_hearing(
            hearing_id, store=repo, create_session_kwargs=session_kwargs, **kwargs
        )
    except hearing_pipeline.PipelineError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ai_mode.AiModeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"processing failed: {exc}"[:400]) from exc
    return {**result, "hearing": result["hearing"].model_dump(mode="json")}


@router.get("/{hearing_id}/proceedings")
async def get_proceedings(hearing_id: UUID, context=Depends(require_organisation)):
    _, organisation_id = context
    hearing = _repo(organisation_id).get_hearing(hearing_id)
    meta = hearing.platform_metadata or {}
    return {
        "hearing_id": str(hearing_id),
        "status": hearing.status.value,
        "pipeline": meta.get("pipeline"),
        "asr": meta.get("asr"),
        "proceedings": meta.get("proceedings"),
    }


@router.post("/{hearing_id}/review")
async def review_hearing(
    hearing_id: UUID,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    try:
        hearing = _repo(organisation_id).mark_reviewed(hearing_id, actor=user.email or user.id)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return hearing.model_dump(mode="json")


@router.post("/{hearing_id}/capture/start")
async def start_capture(
    hearing_id: UUID,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    """Join via official Teams calling-bot or Zoom Meeting SDK when configured."""
    _, organisation_id = context
    repo = _repo(organisation_id)
    hearing = repo.get_hearing(hearing_id)
    from app.services.court_adapters import live_capture

    try:
        result = await live_capture.start_capture(hearing, store=repo)
    except live_capture.CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (InvalidTransition, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.post("/{hearing_id}/capture/stop")
async def stop_capture(
    hearing_id: UUID,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    _, organisation_id = context
    repo = _repo(organisation_id)
    hearing = repo.get_hearing(hearing_id)
    from app.services.court_adapters import live_capture

    try:
        result = await live_capture.stop_capture(hearing, store=repo)
    except live_capture.CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (InvalidTransition, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result
