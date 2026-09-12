"""
Endpoints called by the deployed Trigger.dev tasks (trigger/detectActions.ts,
trigger/generateActions.ts), not by the frontend. Hold the real logic —
the Trigger.dev tasks are thin relays that call these over HTTP so the
work runs as a durable, retried background job. Protected by a shared
secret rather than user auth, since the caller is our own trigger.dev
project, not an end user.

When TRIGGER_SECRET_KEY isn't configured, these endpoints simply never
get called — /sessions/{id}/detect and /generate fall back to invoking
action_detector.py / action_executor.py directly in-process instead.
"""

import os
import uuid

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import DetectedAction, FlaggedMoment, Matter, TranscriptSegment
from app.services import action_detector, action_executor

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
