import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import TranscriptSegment
from app.services import storage, transcription

router = APIRouter()


@router.websocket("/{session_id}/stream")
async def stream_audio(websocket: WebSocket, session_id: uuid.UUID):
    await websocket.accept()

    detail = storage.get_session(session_id)
    if detail is None:
        await websocket.close(code=4404)
        return

    provider = transcription.get_provider()
    elapsed_ms = 0

    try:
        while True:
            # Client sends raw audio chunk bytes (e.g. ~2-3s of WAV/PCM).
            # Chunk size is a client-side decision — smaller chunks feel
            # more "live" but cost more per-chunk overhead.
            audio_bytes = await websocket.receive_bytes()
            chunk_ms = 3000  # assumes the client sends fixed ~3s chunks

            result = await provider.transcribe_chunk(audio_bytes, language_hint=detail.language_hint)
            if not (result.text or "").strip():
                elapsed_ms += chunk_ms
                continue

            speaker = None
            if isinstance(result.raw, dict):
                speaker = result.raw.get("speaker") or result.raw.get("speaker_label")
            if not speaker:
                existing = storage.get_transcript(session_id)
                speaker = existing[-1].speaker if existing and existing[-1].speaker else "Speaker 1"

            segment = TranscriptSegment(
                session_id=session_id,
                speaker=speaker,
                text=result.text.strip(),
                start_ms=elapsed_ms,
                end_ms=elapsed_ms + chunk_ms,
                confidence=result.confidence,
                source_raw=result.raw,
            )
            storage.append_segment(session_id, segment)
            elapsed_ms += chunk_ms

            # Push the partial transcript straight back to the client.
            await websocket.send_json(segment.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
