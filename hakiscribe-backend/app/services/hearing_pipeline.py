"""Post-hearing processing: recording / platform transcript → segments → record.

  ingest_recording()   store audio bytes, attach to hearing
  ingest_transcript()  store a platform WebVTT transcript (Teams / Zoom)
  process_hearing()    transcribe (or parse VTT) → session transcript →
                       proceedings intelligence → status `transcribed`

ASR follows the active AI mode (`ai_mode.resolve_asr_provider_name`), so a
local_only deployment transcribes on local Whisper and extracts with Ollama.
Processing refuses to run until a human has confirmed the matter link.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from app.models.schemas import HearingStatus, SessionStatus, TranscriptSegment
from app.services import hearings, proceedings_intel, recording_store, storage, vtt

logger = logging.getLogger(__name__)

VTT_SUFFIX = ".vtt"


class PipelineError(RuntimeError):
    pass


def ingest_recording(
    hearing_id: UUID,
    filename: Optional[str],
    data: bytes,
    content_type: Optional[str] = None,
    *,
    store: Any = None,
):
    if not data:
        raise ValueError("empty recording")
    store = store or hearings
    stored = recording_store.save(hearing_id, filename, data, content_type or "application/octet-stream")
    return store.attach_recording(
        hearing_id,
        object_key=stored["key"],
        meta={"filename": filename, "bytes": stored["bytes"], "content_type": stored["content_type"], "s3": stored["s3"], "kind": "audio"},
    )


def ingest_transcript(hearing_id: UUID, vtt_text: str, *, origin: str, store: Any = None):
    """Store a platform transcript; it is processed instead of running ASR."""
    if not vtt.parse(vtt_text):
        raise ValueError("transcript contained no timed cues")
    store = store or hearings
    data = vtt_text.encode("utf-8")
    stored = recording_store.save(hearing_id, f"{origin}-transcript{VTT_SUFFIX}", data, "text/vtt")
    return store.attach_recording(
        hearing_id,
        object_key=stored["key"],
        meta={"filename": stored["key"].rsplit("/", 1)[-1], "bytes": stored["bytes"], "content_type": "text/vtt", "kind": "platform_transcript", "origin": origin},
    )


async def _segments_from_audio(data: bytes, filename: str, language_hint: Optional[str], diarize: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from app.services import ai_mode, transcription

    name = ai_mode.resolve_asr_provider_name()  # raises AiModeError when forbidden
    provider = transcription._provider_for_name(name)

    if isinstance(provider, transcription.LocalWhisperProvider):
        result = await provider.transcribe_file(data, filename=filename, language_hint=language_hint, diarize=diarize)
        segs = [
            {
                "start_ms": int(float(s["start"]) * 1000),
                "end_ms": int(float(s["end"]) * 1000),
                "speaker": s.get("speaker"),
                "text": s["text"],
                "confidence": None,
            }
            for s in result.raw.get("segments") or []
        ]
        meta = {
            "asr_provider": name,
            "language": result.raw.get("language"),
            "language_probability": result.raw.get("language_probability"),
            "duration_s": result.raw.get("duration"),
            "diarization": result.raw.get("diarization"),
            "segmentation": "timestamped",
        }
        return segs, meta

    if isinstance(provider, transcription.IntronVoiceProvider):
        result = await provider.transcribe_file(data, filename=filename, language_hint=language_hint, legal=True)
    else:
        result = await provider.transcribe_chunk(data, language_hint)
    if result.raw.get("error"):
        raise PipelineError(f"ASR provider '{name}' failed: {result.raw.get('error')}")
    if not result.text.strip():
        return [], {"asr_provider": name, "segmentation": "none"}
    # Providers without timestamps yield one segment; say so rather than invent timings.
    return (
        [{"start_ms": 0, "end_ms": 0, "speaker": None, "text": result.text.strip(), "confidence": result.confidence}],
        {"asr_provider": name, "segmentation": "single_block_no_timestamps"},
    )


async def process_hearing(
    hearing_id: UUID,
    *,
    use_llm: bool = True,
    diarize: bool = False,
    language_hint: Optional[str] = None,
    store: Any = None,
    create_session_kwargs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    store = store or hearings
    hearing = store.get_hearing(hearing_id)
    if hearing is None:
        raise KeyError("hearing_not_found")
    if hearing.matter_id is None:
        raise PipelineError("Confirm the matter link before processing this hearing")
    if not hearing.recording_object_key:
        raise PipelineError("No recording or transcript attached to this hearing")
    if hearing.status not in (HearingStatus.ingested, HearingStatus.transcribed):
        raise PipelineError(f"Hearing is {hearing.status.value}; expected ingested or transcribed")

    store.set_pipeline_state(hearing_id, state="running", step="load", error=None)
    try:
        data = recording_store.load(hearing.recording_object_key)
        if data is None:
            raise PipelineError(f"Stored recording missing: {hearing.recording_object_key}")

        session_result = store.create_session_from_hearing(hearing_id, **(create_session_kwargs or {}))
        session = session_result["session"]
        store.set_pipeline_state(hearing_id, step="transcribe")
        if hearing.recording_object_key.endswith(VTT_SUFFIX):
            raw_segments = vtt.parse(data.decode("utf-8", errors="replace"))
            asr_meta: dict[str, Any] = {"asr_provider": "platform_transcript", "segmentation": "timestamped"}
        else:
            filename = hearing.recording_object_key.rsplit("/", 1)[-1]
            raw_segments, asr_meta = await _segments_from_audio(data, filename, language_hint, diarize)
        if not raw_segments:
            raise PipelineError("Transcription produced no speech segments")

        segments = [
            TranscriptSegment(
                session_id=session.id,
                speaker=s.get("speaker"),
                text=s["text"],
                start_ms=s["start_ms"],
                end_ms=s["end_ms"],
                confidence=s.get("confidence"),
                source_raw={"hearing_id": str(hearing_id), "provider": asr_meta.get("asr_provider")},
            )
            for s in raw_segments
        ]
        if hasattr(store, "write_transcript_segments"):
            actor = (create_session_kwargs or {}).get("user_id") or "pipeline"
            store.write_transcript_segments(session.id, segments, user_id=str(actor))
            if hasattr(store, "mark_session_ready"):
                store.mark_session_ready(session.id)
            transcript_for_intel = segments
        else:
            storage.replace_transcript(session.id, segments)
            if asr_meta.get("language"):
                storage.update_session_fields(session.id, detected_language=asr_meta["language"])
            storage.update_session_status(session.id, SessionStatus.ready)
            transcript_for_intel = storage.get_transcript(session.id)
        if hearing.status == HearingStatus.ingested:
            store.transition(hearing, HearingStatus.transcribed)

        store.set_pipeline_state(hearing_id, step="proceedings")
        record = await proceedings_intel.extract(transcript_for_intel, use_llm=use_llm)
        hearing.platform_metadata = {**(hearing.platform_metadata or {}), "asr": asr_meta, "proceedings": record}
        # Persist proceedings onto the hearing row / snapshot.
        if hasattr(store, "upsert"):
            store.upsert(hearing)
        elif hasattr(store, "set_pipeline_state"):
            pass
        store.set_pipeline_state(hearing_id, state="done", step="complete", segments=len(segments))
        hearing = store.get_hearing(hearing_id) or hearing
    except Exception as exc:
        store.set_pipeline_state(hearing_id, state="error", error=str(exc)[:500])
        raise
    return {
        "hearing": hearing,
        "session_id": str(session.id),
        "segments": len(segments),
        "asr": asr_meta,
        "proceedings": record,
    }
