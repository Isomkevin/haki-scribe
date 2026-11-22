"""Optional speaker diarization for the local Whisper server.

pyannote.audio is heavy (torch) and its pipeline weights are gated on Hugging
Face, so diarization is strictly opt-in:

  DIARIZATION_ENABLED=1
  HF_TOKEN=<token with access to pyannote/speaker-diarization-3.1>
  pip install pyannote.audio   (see requirements-diarization.txt)

When any of those is missing, `diarize()` returns None with a reason and the
transcription response says so — speakers are never invented.
"""

from __future__ import annotations

import os
from typing import Any, Optional

_pipeline: Any = None
_load_error: Optional[str] = None


def enabled() -> bool:
    return (os.environ.get("DIARIZATION_ENABLED") or "").strip().lower() in ("1", "true", "yes")


def status() -> dict[str, Any]:
    if not enabled():
        return {"enabled": False, "reason": "DIARIZATION_ENABLED is not set"}
    if _load_error:
        return {"enabled": False, "reason": _load_error}
    return {"enabled": True, "loaded": _pipeline is not None, "model": _model_id()}


def _model_id() -> str:
    return os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1")


def _get_pipeline():
    global _pipeline, _load_error
    if _pipeline is not None or _load_error:
        return _pipeline
    token = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if not token:
        _load_error = "HF_TOKEN is not set (pyannote weights are gated)"
        return None
    try:
        from pyannote.audio import Pipeline  # type: ignore[import-not-found]
    except ImportError:
        _load_error = "pyannote.audio is not installed"
        return None
    try:
        _pipeline = Pipeline.from_pretrained(_model_id(), use_auth_token=token)
    except Exception as exc:  # noqa: BLE001
        _load_error = f"pyannote pipeline failed to load: {exc}"[:300]
        return None
    return _pipeline


def diarize(audio_path: str) -> tuple[Optional[list[dict[str, Any]]], Optional[str]]:
    """Return ([{start, end, speaker}], None) or (None, reason)."""
    if not enabled():
        return None, "DIARIZATION_ENABLED is not set"
    pipeline = _get_pipeline()
    if pipeline is None:
        return None, _load_error
    try:
        annotation = pipeline(audio_path)
    except Exception as exc:  # noqa: BLE001
        return None, f"diarization failed: {exc}"[:300]
    turns = [
        {"start": float(turn.start), "end": float(turn.end), "speaker": str(label)}
        for turn, _track, label in annotation.itertracks(yield_label=True)
    ]
    return turns, None


def assign_speakers(segments: list[dict[str, Any]], turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Label each ASR segment with the diarization speaker it overlaps most.

    Speaker ids are renumbered in order of first appearance ("Speaker 1", …)
    so labels are stable and readable. Segments with no overlap stay None.
    """
    friendly: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    for seg in segments:
        s, e = float(seg["start"]), float(seg["end"])
        totals: dict[str, float] = {}
        for turn in turns:
            overlap = min(e, turn["end"]) - max(s, turn["start"])
            if overlap > 0:
                totals[turn["speaker"]] = totals.get(turn["speaker"], 0.0) + overlap
        speaker = None
        if totals:
            raw = max(totals.items(), key=lambda kv: kv[1])[0]
            if raw not in friendly:
                friendly[raw] = f"Speaker {len(friendly) + 1}"
            speaker = friendly[raw]
        out.append({**seg, "speaker": speaker})
    return out
