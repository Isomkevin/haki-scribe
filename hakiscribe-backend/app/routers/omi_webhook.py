import os
import uuid

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import OmiWebhookPayload, TranscriptSegment
from app.services import storage

router = APIRouter()

OMI_SHARED_SECRET = os.environ.get("OMI_SHARED_SECRET", "")


@router.post("/omi")
def receive_omi_transcript(
    payload: OmiWebhookPayload,
    x_omi_secret: str = Header(default=""),
):
    if OMI_SHARED_SECRET and x_omi_secret != OMI_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    if payload.session_external_id is None:
        raise HTTPException(status_code=400, detail="Missing session_external_id")

    try:
        session_id = uuid.UUID(payload.session_external_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_external_id must be a session UUID")

    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # NOTE: adjust field names below once you've checked Omi's actual
    # webhook payload shape against their docs.
    for raw_segment in payload.segments:
        segment = TranscriptSegment(
            session_id=session_id,
            speaker=raw_segment.get("speaker"),
            text=raw_segment.get("text", ""),
            start_ms=raw_segment.get("start_ms", 0),
            end_ms=raw_segment.get("end_ms", 0),
            confidence=raw_segment.get("confidence"),
            source_raw=raw_segment,
        )
        storage.append_segment(session_id, segment)

    return {"received": len(payload.segments)}
