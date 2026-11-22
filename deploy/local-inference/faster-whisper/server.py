"""OpenAI-compatible transcription server for local faster-whisper.

`response_format=json` (default) keeps the original `{text, model}` contract
used by live captions. `response_format=verbose_json` returns timestamped
segments, detected language and (when enabled) diarized speaker labels — the
shape HakiScribe uses for full hearing recordings.
"""

from __future__ import annotations

import os
import re
import tempfile
import threading
import time
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from faster_whisper import WhisperModel

import diarize

app = FastAPI(title="HakiScribe Local Whisper", version="0.2.0")

_model: Optional[WhisperModel] = None
_model_lock = threading.Lock()
_load_error: Optional[str] = None

# Biases decoding toward Kenyan court vocabulary in both languages. Whisper
# treats the prompt as prior context, so this is a vocabulary hint, not text
# to transcribe. Override with WHISPER_LEGAL_PROMPT ("" disables).
DEFAULT_LEGAL_PROMPT = (
    "Kenyan court proceedings in English and Kiswahili. Your Honour, My Lady, "
    "Mheshimiwa, Mahakama, the Court, counsel for the plaintiff, the respondent, "
    "the petitioner, the accused, adjourned, adjournment, mention, hearing date, "
    "ruling, judgment, directions, plaint, affidavit, submissions, exhibit, "
    "cause list, shauri, kesi, mshtakiwa, mlalamikaji, ushahidi, hukumu, tarehe."
)


def _model_id() -> str:
    return os.environ.get("WHISPER_MODEL", "Systran/faster-whisper-large-v3")


def get_model() -> WhisperModel:
    global _model, _load_error
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            try:
                _model = WhisperModel(
                    _model_id(),
                    device=os.environ.get("WHISPER_DEVICE", "cpu"),
                    compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
                )
                _load_error = None
            except Exception as exc:  # noqa: BLE001
                _load_error = str(exc)[:300]
                raise
    return _model


# Measured on FLEURS sw_ke with `small`: the vocabulary prompt raised Kiswahili
# WER (0.66 -> 0.77) and was sometimes emitted verbatim as the "transcript".
# So it is only applied when the caller explicitly asks for these languages.
ECHO_MIN_WORDS = 5


def _legal_prompt(language: Optional[str]) -> Optional[str]:
    langs = {
        code.strip().lower()
        for code in os.environ.get("WHISPER_LEGAL_PROMPT_LANGS", "en").split(",")
        if code.strip()
    }
    if (language or "").lower() not in langs:
        return None
    raw = os.environ.get("WHISPER_LEGAL_PROMPT")
    if raw is None:
        return DEFAULT_LEGAL_PROMPT
    return raw.strip() or None


def _allowed_languages() -> list[str]:
    """Languages auto-detection may choose. Empty = any Whisper language."""
    raw = os.environ.get("WHISPER_ALLOWED_LANGUAGES", "en,sw")
    return [code.strip().lower() for code in raw.split(",") if code.strip()]


def constrain_language(detected: str, probs: Optional[list], allowed: list[str]) -> Optional[str]:
    """Return the allowed language to force when detection chose another one.

    Seen on FLEURS sw_ke: a Kiswahili clip auto-detected as Javanese ("jw").
    """
    if not allowed or detected in allowed:
        return None
    ranked = {code: prob for code, prob in (probs or [])}
    return max(allowed, key=lambda code: ranked.get(code, 0.0))


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", (text or "").lower())


def echoes_prompt(text: str, prompt: Optional[str], min_words: int = ECHO_MIN_WORDS) -> bool:
    """True when `text` repeats >= min_words consecutive words of the prompt.

    Whisper can emit its initial_prompt as if it had been spoken; in a court
    record that is fabricated text, so such segments are dropped.
    """
    if not prompt:
        return False
    p_words = _words(prompt)
    t_words = _words(text)
    if len(t_words) < min_words or len(p_words) < min_words:
        return False
    grams = {tuple(p_words[i : i + min_words]) for i in range(len(p_words) - min_words + 1)}
    return any(tuple(t_words[i : i + min_words]) in grams for i in range(len(t_words) - min_words + 1))


def _vad_parameters() -> dict[str, Any]:
    return {
        "min_silence_duration_ms": int(os.environ.get("WHISPER_VAD_MIN_SILENCE_MS", "500")),
        "speech_pad_ms": int(os.environ.get("WHISPER_VAD_SPEECH_PAD_MS", "400")),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "local_whisper",
        "model": _model_id(),
        "model_loaded": _model is not None,
        "model_error": _load_error,
        "diarization": diarize.status(),
    }


@app.post("/ready")
def ready():
    """Force-load the model so the first hearing does not pay the load cost."""
    try:
        get_model()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"model failed to load: {exc}") from exc
    return health()


@app.get("/v1/models")
def models():
    return {"data": [{"id": _model_id(), "object": "model"}]}


def _transcribe_path(
    path: str,
    *,
    language: Optional[str],
    prompt: Optional[str],
    want_segments: bool,
    want_diarization: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    def run(lang: Optional[str], *, explicit: bool):
        # The vocabulary prompt follows the caller's explicit choice only, never a guess.
        legal = _legal_prompt(lang) if explicit else None
        initial = " ".join(p for p in (legal, prompt) if p) or None
        seg_iter, run_info = get_model().transcribe(
            path,
            language=lang or None,
            initial_prompt=initial,
            vad_filter=True,
            vad_parameters=_vad_parameters(),
            condition_on_previous_text=False,  # limits hallucination loops on long silence
        )
        return seg_iter, run_info, initial

    segments_iter, info, initial_prompt = run(language, explicit=True)
    language_forced_from = None
    if not language:
        # Segments are lazy, so re-running here only costs the language detection.
        forced = constrain_language(info.language, getattr(info, "all_language_probs", None), _allowed_languages())
        if forced:
            language_forced_from = info.language
            segments_iter, info, initial_prompt = run(forced, explicit=False)
    segments: list[dict[str, Any]] = []
    prompt_echo_dropped = 0
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        if echoes_prompt(text, initial_prompt):
            prompt_echo_dropped += 1
            continue
        segments.append(
            {
                "id": len(segments),
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": text,
                "avg_logprob": round(float(seg.avg_logprob), 4),
                "no_speech_prob": round(float(seg.no_speech_prob), 4),
            }
        )
    body: dict[str, Any] = {
        "text": " ".join(s["text"] for s in segments).strip(),
        "model": _model_id(),
    }
    if not want_segments:
        return body

    diarization: dict[str, Any] = {"enabled": False, "reason": "not requested"}
    if want_diarization:
        turns, reason = diarize.diarize(path)
        if turns is None:
            diarization = {"enabled": False, "reason": reason}
        else:
            segments = diarize.assign_speakers(segments, turns)
            diarization = {"enabled": True, "speakers": len({t["speaker"] for t in turns})}
    body.update(
        {
            "language": info.language,
            "language_probability": round(float(info.language_probability), 4),
            "duration": round(float(info.duration), 3),
            "segments": segments,
            "diarization": diarization,
            "prompt_applied": bool(initial_prompt),
            "language_forced_from": language_forced_from,
            "prompt_echo_dropped": prompt_echo_dropped,
            "processing_ms": int((time.perf_counter() - started) * 1000),
        }
    )
    return body


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
    diarize_speakers: Optional[bool] = Form(False),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty audio upload")
    fmt = (response_format or "json").lower()
    if fmt not in ("json", "verbose_json", "text"):
        raise HTTPException(status_code=400, detail=f"unsupported response_format: {response_format}")
    suffix = os.path.splitext(file.filename or "chunk.webm")[1] or ".webm"
    # delete=False: Windows cannot reopen a NamedTemporaryFile that is still open.
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(raw)
        tmp.close()
        try:
            body = await run_in_threadpool(
                _transcribe_path,
                tmp.name,
                language=language,
                prompt=prompt,
                want_segments=fmt == "verbose_json",
                want_diarization=bool(diarize_speakers),
            )
        except Exception as exc:  # noqa: BLE001
            # Undecodable audio is the caller's problem (422); anything else is ours (500).
            status = 422 if type(exc).__module__.split(".")[0] == "av" else 500
            raise HTTPException(status_code=status, detail=f"transcription failed: {exc}"[:400]) from exc
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    if fmt == "text":
        return body["text"]
    if model:
        body["requested_model"] = model
    return body
