"""WebVTT → timestamped, speaker-labelled segments.

Handles the two transcript dialects virtual courts produce:
  Teams:  <v Jane Wanjiru>Good morning, Your Honour.</v>
  Zoom:   Jane Wanjiru: Good morning, Your Honour.
Platform transcripts carry real participant names, so they are a better
speaker source than acoustic diarization when the platform provides them.
"""

from __future__ import annotations

import re
from typing import Any, Optional

_TIMING = re.compile(
    r"(?P<s>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*(?P<e>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})"
)
_VOICE = re.compile(r"<v(?:\.[^\s>]*)?\s+([^>]+)>")
_TAG = re.compile(r"</?[^>]+>")
_ZOOM_SPEAKER = re.compile(r"^([^:\n]{1,60}):\s+(.+)$", re.S)


def _to_ms(stamp: str) -> int:
    parts = stamp.replace(",", ".").split(":")
    if len(parts) == 2:
        parts = ["0", *parts]
    h, m, s = parts
    return int(round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000))


def _speaker_and_text(lines: list[str]) -> tuple[Optional[str], str]:
    raw = " ".join(line.strip() for line in lines if line.strip())
    speaker: Optional[str] = None
    voice = _VOICE.search(raw)
    if voice:
        speaker = voice.group(1).strip()
    text = _TAG.sub("", raw).strip()
    if speaker is None:
        m = _ZOOM_SPEAKER.match(text)
        # Avoid treating "Note: …" style prose as a speaker: require a name-like label.
        if m and re.match(r"^[A-Z][\w.'\- ]*$", m.group(1).strip()):
            speaker, text = m.group(1).strip(), m.group(2).strip()
    return speaker, re.sub(r"\s+", " ", text)


def parse(vtt: str) -> list[dict[str, Any]]:
    """Return [{start_ms, end_ms, speaker, text}] in cue order.

    Consecutive cues from the same speaker are kept separate so timestamps
    stay precise for quote grounding.
    """
    text = vtt.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    segments: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.split("\n")
        idx = next((i for i, line in enumerate(lines) if _TIMING.search(line)), None)
        if idx is None:
            continue  # header, NOTE, STYLE, or cue without timing
        timing = _TIMING.search(lines[idx])
        assert timing is not None
        speaker, body = _speaker_and_text(lines[idx + 1 :])
        if not body:
            continue
        segments.append(
            {
                "start_ms": _to_ms(timing.group("s")),
                "end_ms": _to_ms(timing.group("e")),
                "speaker": speaker,
                "text": body,
            }
        )
    return segments
