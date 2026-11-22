"""Minimal OpenAI-compatible transcription server for local faster-whisper."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="HakiScribe Local Whisper", version="0.1.0")

_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            os.environ.get("WHISPER_MODEL", "Systran/faster-whisper-large-v3"),
            device=os.environ.get("WHISPER_DEVICE", "cpu"),
            compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        )
    return _model


@app.get("/health")
def health():
    return {"status": "ok", "provider": "local_whisper"}


@app.get("/v1/models")
def models():
    mid = os.environ.get("WHISPER_MODEL", "Systran/faster-whisper-large-v3")
    return {"data": [{"id": mid, "object": "model"}]}


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    raw = await file.read()
    suffix = os.path.splitext(file.filename or "chunk.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(raw)
        tmp.flush()
        segments, _info = get_model().transcribe(
            tmp.name,
            language=language or None,
            initial_prompt=prompt or None,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments if seg.text).strip()
    return {"text": text, "model": model or os.environ.get("WHISPER_MODEL")}
