import uuid

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FlagCreate,
    FlaggedMoment,
    SegmentRedactRequest,
    Session,
    SessionCreate,
    SessionDetail,
    SessionLibraryItem,
    SessionStatus,
    SpeakerRelabelRequest,
    TranscriptSegment,
)
from app.services import storage

router = APIRouter()


@router.post("", response_model=Session)
def create_session(payload: SessionCreate):
    session = Session(**payload.model_dump())
    return storage.create_session(session)


@router.get("", response_model=list[SessionLibraryItem])
def list_sessions():
    return storage.list_library_sessions()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: uuid.UUID):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail


@router.post("/{session_id}/finalize", response_model=Session)
def finalize_session(session_id: uuid.UUID):
    session = storage.update_session_status(session_id, SessionStatus.ready)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/flags", response_model=FlaggedMoment)
def flag_moment(session_id: uuid.UUID, payload: FlagCreate):
    """No-look bookmark dropped during recording (the 'Flag this moment'
    button) — call this the instant the user taps it, don't wait for Stop."""
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    flag = FlaggedMoment(session_id=session_id, **payload.model_dump())
    storage.add_flag(session_id, flag)
    return flag


@router.post("/{session_id}/speakers", response_model=list[TranscriptSegment])
def relabel_speakers(session_id: uuid.UUID, payload: SpeakerRelabelRequest):
    """Call once, after Stop and before /detect — mapping raw diarization
    labels ('Speaker 1') to real names improves every downstream action."""
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return storage.relabel_speakers(session_id, payload.mapping)


@router.patch("/{session_id}/segments/{segment_id}", response_model=TranscriptSegment)
def redact_segment(session_id: uuid.UUID, segment_id: uuid.UUID, payload: SegmentRedactRequest):
    """Mark a segment privileged/off-record so it's excluded from /detect.
    Toggle-able — call again with redacted: false to un-redact."""
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    segment = storage.set_segment_redacted(session_id, segment_id, payload.redacted)
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment

