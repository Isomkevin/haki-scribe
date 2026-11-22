"""
Endpoints called by the deployed Trigger.dev tasks (trigger/detectActions.ts,
trigger/generateActions.ts, trigger/processHearing.ts), not by the frontend.
Hold the real logic — the Trigger.dev tasks are thin relays that call these
over HTTP so the work runs as a durable, retried background job. Protected by
a shared secret rather than user auth, since the caller is our own trigger.dev
project, not an end user.

When TRIGGER_SECRET_KEY isn't configured, these endpoints simply never
get called — callers fall back to in-process execution instead.
"""

import os
import uuid

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import DetectedAction, FlaggedMoment, Matter, TranscriptSegment
from app.services import action_detector, action_executor, hearing_pipeline

router = APIRouter()

INTERNAL_SECRET = os.environ.get("BACKEND_INTERNAL_SECRET", "")


def _check_secret(x_internal_secret: str) -> None:
    if INTERNAL_SECRET and x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal secret")


@router.post("/detect")
async def internal_detect(body: dict, x_internal_secret: str = Header(default="")):
    _check_secret(x_internal_secret)
    session_id = uuid.UUID(body["session_id"])
    transcript = [TranscriptSegment(**seg) for seg in body.get("transcript", [])]
    flags = [FlaggedMoment(**f) for f in body.get("flags", [])]
    known_matters = [Matter(**m) for m in body.get("known_matters", [])]

    actions = await action_detector.detect_actions(
        session_id,
        transcript,
        flags=flags,
        known_matters=known_matters,
        session_title=body.get("session_title"),
    )
    return [a.model_dump(mode="json") for a in actions]


@router.post("/generate")
async def internal_generate(body: dict, x_internal_secret: str = Header(default="")):
    _check_secret(x_internal_secret)
    actions = [DetectedAction(**a) for a in body.get("actions", [])]
    transcript = [TranscriptSegment(**seg) for seg in body.get("transcript", [])]

    results = await action_executor.execute_actions(actions, transcript=transcript or None)
    return [result.model_dump(mode="json") for result in results]


@router.post("/process-hearing")
async def internal_process_hearing(body: dict, x_internal_secret: str = Header(default="")):
    """Durable hearing transcription + proceedings (Trigger process-hearing relay)."""
    _check_secret(x_internal_secret)
    hearing_id = uuid.UUID(body["hearing_id"])
    kwargs = {
        "use_llm": bool(body.get("use_llm", True)),
        "diarize": bool(body.get("diarize", False)),
        "language_hint": body.get("language_hint"),
    }
    org_raw = body.get("organisation_id")
    try:
        if org_raw:
            from app.services.production_hearings import ProductionHearingsRepo
            from app.services.tenant_context import production_client

            repo = ProductionHearingsRepo(production_client(), uuid.UUID(str(org_raw)))
            result = await hearing_pipeline.process_hearing(
                hearing_id,
                store=repo,
                create_session_kwargs={
                    "workspace_id": uuid.UUID(str(body["workspace_id"])),
                    "user_id": str(body.get("user_id") or "trigger"),
                },
                **kwargs,
            )
        else:
            result = await hearing_pipeline.process_hearing(hearing_id, **kwargs)
    except hearing_pipeline.PipelineError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    hearing = result["hearing"]
    return {
        "hearing": hearing.model_dump(mode="json") if hasattr(hearing, "model_dump") else hearing,
        "session_id": result.get("session_id"),
        "segments": result.get("segments"),
        "asr": result.get("asr"),
        "proceedings": result.get("proceedings"),
    }
