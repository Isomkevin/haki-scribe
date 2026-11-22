"""Virtual court hearings API — import, match, confirm, session, upload."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource
from app.services import hearing_pipeline, recording_store
from app.services import hearings as hearings_service
from app.services.court_adapters import AdapterError, GoogleCalendarAdapter, TeamsGraphAdapter, ZoomAdapter

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
    from app.services.court_adapters import teams_bot, zoom_bot

    adapters = [
        GoogleCalendarAdapter(),
        TeamsGraphAdapter(),
        ZoomAdapter(),
        teams_bot.TeamsCallingBot(),
        zoom_bot.ZoomMeetingBot(),
    ]
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
    except hearings_service.InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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




def _require(hearing_id: UUID):
    hearing = hearings_service.get_hearing(hearing_id)
    if not hearing:
        raise HTTPException(status_code=404, detail="Hearing not found")
    return hearing


def _ingest_error(exc: Exception) -> HTTPException:
    if isinstance(exc, recording_store.RecordingTooLarge):
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, hearings_service.InvalidTransition):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/{hearing_id}/upload")
async def upload_recording(hearing_id: UUID, file: UploadFile = File(...)):
    """Attach a recording. Bytes persist to the recordings volume (+ S3 when configured)."""
    _require(hearing_id)
    raw = await file.read()
    try:
        updated = hearing_pipeline.ingest_recording(hearing_id, file.filename, raw, file.content_type)
    except (ValueError, hearings_service.InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return updated.model_dump(mode="json")


@router.post("/{hearing_id}/transcript")
async def upload_transcript(hearing_id: UUID, file: UploadFile = File(...)):
    """Attach a platform WebVTT transcript (Teams / Zoom export) instead of audio."""
    _require(hearing_id)
    raw = await file.read()
    try:
        updated = hearing_pipeline.ingest_transcript(hearing_id, raw.decode("utf-8", errors="replace"), origin="upload")
    except (ValueError, hearings_service.InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return updated.model_dump(mode="json")


_FETCH_ADAPTERS = {"zoom": ZoomAdapter, "teams_graph": TeamsGraphAdapter}


@router.post("/{hearing_id}/fetch-recording")
async def fetch_recording(hearing_id: UUID, prefer: str = Query("audio", pattern="^(audio|transcript)$")):
    """Pull the recording or transcript from Zoom / Teams through their official APIs."""
    hearing = _require(hearing_id)
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
                hearing_id, artifact.data.decode("utf-8", errors="replace"), origin=hearing.source.value
            )
        else:
            updated = hearing_pipeline.ingest_recording(hearing_id, artifact.filename, artifact.data, artifact.content_type)
    except (ValueError, hearings_service.InvalidTransition) as exc:
        raise _ingest_error(exc) from exc
    return {"hearing": updated.model_dump(mode="json"), "artifact": {"kind": artifact.kind, **artifact.metadata}}


async def _process_in_background(hearing_id: UUID, **kwargs: Any) -> None:
    try:
        await hearing_pipeline.process_hearing(hearing_id, **kwargs)
    except Exception:  # noqa: BLE001 — error is recorded in platform_metadata.pipeline
        pass


@router.post("/{hearing_id}/process")
async def process_hearing(
    hearing_id: UUID,
    background_tasks: BackgroundTasks,
    wait: bool = Query(False, description="Run inline and return the result (long recordings may time out)"),
    use_llm: bool = Query(True),
    diarize: bool = Query(False),
    language_hint: Optional[str] = Query(None),
):
    """Transcribe + extract the hearing record. Requires a confirmed matter link."""
    hearing = _require(hearing_id)
    kwargs = {"use_llm": use_llm, "diarize": diarize, "language_hint": language_hint}
    if not wait:
        if hearing.matter_id is None:
            raise HTTPException(status_code=409, detail="Confirm the matter link before processing this hearing")
        from app.services import ai_mode, trigger_client

        hearings_service.set_pipeline_state(hearing_id, state="queued", step="queued", error=None)
        run_id = None
        if not ai_mode.prefer_in_process_jobs():
            run_id = await trigger_client.trigger_enqueue(
                "process-hearing",
                {"hearing_id": str(hearing_id), **kwargs},
            )
        if run_id:
            hearings_service.set_pipeline_state(
                hearing_id, job_id=run_id, run_id=run_id, queue="trigger"
            )
            return {"status": "queued", "run_id": run_id, "hearing": hearing.model_dump(mode="json")}
        background_tasks.add_task(_process_in_background, hearing_id, **kwargs)
        return {"status": "queued", "hearing": hearing.model_dump(mode="json")}
    from app.services import ai_mode

    try:
        result = await hearing_pipeline.process_hearing(hearing_id, **kwargs)
    except hearing_pipeline.PipelineError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ai_mode.AiModeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface ASR / network failures honestly
        raise HTTPException(status_code=502, detail=f"processing failed: {exc}"[:400]) from exc
    return {**result, "hearing": result["hearing"].model_dump(mode="json")}


@router.post("/{hearing_id}/capture/start")
async def start_capture(hearing_id: UUID):
    hearing = _require(hearing_id)
    from app.services.court_adapters import live_capture

    try:
        return await live_capture.start_capture(hearing)
    except live_capture.CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (hearings_service.InvalidTransition, ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{hearing_id}/capture/stop")
async def stop_capture(hearing_id: UUID):
    hearing = _require(hearing_id)
    from app.services.court_adapters import live_capture

    try:
        return await live_capture.stop_capture(hearing)
    except live_capture.CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (hearings_service.InvalidTransition, ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{hearing_id}/proceedings")
def get_proceedings(hearing_id: UUID):
    hearing = _require(hearing_id)
    meta = hearing.platform_metadata or {}
    return {
        "hearing_id": str(hearing_id),
        "status": hearing.status.value,
        "pipeline": meta.get("pipeline"),
        "asr": meta.get("asr"),
        "proceedings": meta.get("proceedings"),
    }


@router.post("/{hearing_id}/review")
def review_hearing(hearing_id: UUID):
    """Human sign-off on the transcript and extracted record (required before filing)."""
    _require(hearing_id)
    try:
        hearing = hearings_service.mark_reviewed(hearing_id)
    except hearings_service.InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return hearing.model_dump(mode="json")
