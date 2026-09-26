import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from typing import Optional

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
from app.services import demo_library, storage, transcription, workspace

router = APIRouter()


@router.post("", response_model=Session)
def create_session(payload: SessionCreate):
    session = Session(**payload.model_dump())
    return storage.create_session(session)


@router.get("", response_model=list[SessionLibraryItem])
async def list_sessions(include_demo: bool = Query(default=True)):
    if include_demo:
        await demo_library.sync_demo_library()
    return storage.list_library_sessions()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: uuid.UUID):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail


@router.post("/{session_id}/asr/finalize", response_model=SessionDetail)
async def finalize_asr_with_sahara(
    session_id: uuid.UUID,
    audio: UploadFile = File(..., description="Full mic recording (WebM/WAV/…) for Sahara refine"),
    detected_mode: Optional[str] = Form(None),
):
    """Replace live Whisper captions with Intron Sahara (legal court-hearing mode).

    Triggered for African pair/monolingual hints, code-switch/multilingual, or when
    live captions were auto-detected as mixed. Default live ASR unchanged.
    """
    from app.services import language_detect

    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not transcription.intron_configured():
        raise HTTPException(
            status_code=400,
            detail="Intron Sahara is not connected. Add the Intron connector in Settings or set INTRON_API_KEY.",
        )

    prior = storage.get_transcript(session_id)
    transcript_text = " ".join(seg.text for seg in prior if (seg.text or "").strip())
    mix = language_detect.detect_language_mix(transcript_text)
    mode = (detected_mode or "").strip() or mix.mode
    if mode in ("code-switch", "multilingual") or (mode and "-" in mode) or mode in (
        "en",
        "sw",
        "ha",
        "yo",
        "ig",
        "zu",
        "xh",
        "rw",
        "lg",
        "pcm",
        "fr",
        "am",
    ):
        storage.update_session_fields(session_id, detected_language=mode)

    if not language_detect.needs_sahara_refine(detail.language_hint, detected_mode=mode, transcript_text=transcript_text):
        raise HTTPException(
            status_code=400,
            detail="Sahara refine is for African language / code-switch sessions (explicit or auto-detected).",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    # Soft guidance for Sahara sync ≤120s — refuse obviously huge uploads (~3MB/min webm ballpark × 3).
    if len(audio_bytes) > 12_000_000:
        raise HTTPException(
            status_code=400,
            detail="Audio is too large for Sahara sync (keep recordings under ~90 seconds).",
        )

    filename = audio.filename or transcription.chunk_filename(audio_bytes)
    sahara_hint = language_detect.effective_language_hint(
        detail.language_hint,
        detected_mode=mode,
        transcript_text=transcript_text,
    )
    provider = transcription.IntronVoiceProvider()
    result = await provider.transcribe_file(
        audio_bytes,
        filename=filename,
        language_hint=sahara_hint,
        legal=True,
    )
    if not (result.text or "").strip():
        err = (result.raw or {}).get("error") if isinstance(result.raw, dict) else None
        raise HTTPException(
            status_code=502,
            detail=f"Sahara returned no transcript{f' ({err})' if err else ''}. Live captions were kept.",
        )

    # Split on blank lines / sentence-ish breaks so speaker UI still has rows to label.
    chunks = [part.strip() for part in result.text.replace("\r\n", "\n").split("\n") if part.strip()]
    if not chunks:
        chunks = [result.text.strip()]

    # Estimate duration from prior live segments when available.
    total_ms = prior[-1].end_ms if prior else max(3000, len(chunks) * 4000)
    slice_ms = max(1000, total_ms // len(chunks))

    segments: list[TranscriptSegment] = []
    for index, text in enumerate(chunks):
        start_ms = index * slice_ms
        segments.append(
            TranscriptSegment(
                session_id=session_id,
                speaker="Speaker 1",
                text=text,
                start_ms=start_ms,
                end_ms=start_ms + slice_ms,
                confidence=result.confidence,
                source_raw={
                    **(result.raw if isinstance(result.raw, dict) else {"raw": result.raw}),
                    "provider": "sahara",
                    "detected_language": mode,
                    "language_detect_reason": mix.reason,
                },
            )
        )
    storage.replace_transcript(session_id, segments)
    workspace.capture_speaker_contacts(session_id)
    refreshed = storage.get_session(session_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return refreshed


@router.post("/{session_id}/finalize", response_model=Session)
def finalize_session(session_id: uuid.UUID):
    session = storage.update_session_status(session_id, SessionStatus.ready)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    workspace.capture_speaker_contacts(session_id)
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
    segments = storage.relabel_speakers(session_id, payload.mapping)
    workspace.capture_speaker_contacts(session_id)
    return segments


@router.patch("/{session_id}/segments/{segment_id}", response_model=TranscriptSegment)
def redact_segment(session_id: uuid.UUID, segment_id: uuid.UUID, payload: SegmentRedactRequest):
    """Mark a segment privileged/off-record so it's excluded from /detect,
    or correct the transcript text before analysis."""
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.redacted is None and payload.text is None:
        raise HTTPException(status_code=400, detail="Provide redacted and/or text")
    segment = storage.update_segment(session_id, segment_id, redacted=payload.redacted, text=payload.text)
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment

