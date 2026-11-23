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
from app.services import action_detector, action_executor, hearing_jobs

router = APIRouter()

INTERNAL_SECRET = os.environ.get("BACKEND_INTERNAL_SECRET", "")


def _check_secret(x_internal_secret: str) -> None:
    if not INTERNAL_SECRET and hearing_jobs.production_mode():
        # Fail closed: in production these endpoints act on tenant data.
        raise HTTPException(status_code=503, detail="BACKEND_INTERNAL_SECRET is not configured")
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
    """Trigger.dev process-hearing relay: claim and run one queued hearing job.

    The payload names only the job; organisation, workspace and user come from
    the job row written by the authenticated /process request, so a caller
    cannot point the pipeline at another organisation's hearing.
    """
    _check_secret(x_internal_secret)
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    wid = f"trigger:{hearing_jobs.worker_id()}"
    job = hearing_jobs.claim_job(str(job_id), wid)
    if job is None:
        # Already done, or another worker holds it. 200 so Trigger does not retry.
        return {"status": "not_claimed", "job_id": job_id}
    status = await hearing_jobs.run_job(job, wid)
    return {"status": status, "job_id": job_id, "hearing_id": job["hearing_id"]}
