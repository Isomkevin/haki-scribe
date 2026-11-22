"""Proceedings intelligence for hearing transcripts, grounded in quotes.

Two extractors, always labelled by `method` so nothing is passed off as the other:

  rules — deterministic English/Kiswahili patterns for adjournments and next
          dates. No AI, works in every mode, including with no model running.
  llm   — the AI-mode-routed model (Ollama in local_only, Nebius/OpenRouter in
          cloud, per-route in hybrid) extracts outcome, next dates, orders,
          directions and appearances.

Every LLM item must carry a verbatim quote that resolves to a real,
non-privileged transcript segment. Items that do not resolve are moved to
`ungrounded` and never presented as findings.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import date, datetime, timezone
from typing import Any, Optional

from app.models.schemas import TranscriptSegment

logger = logging.getLogger(__name__)

_MONTHS = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Kiswahili
    "januari": 1, "februari": 2, "machi": 3, "aprili": 4, "mei": 5, "juni": 6,
    "julai": 7, "agosti": 8, "septemba": 9, "oktoba": 10, "novemba": 11, "desemba": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_DATE_PATTERNS = [
    # 12th March 2025 / 12 Machi 2025
    re.compile(rf"\b(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m>{_MONTH_ALT})\.?,?\s+(?P<y>\d{{4}})\b", re.I),
    # March 12, 2025
    re.compile(rf"\b(?P<m>{_MONTH_ALT})\.?\s+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y>\d{{4}})\b", re.I),
    # 12/03/2025, 12.03.2025, 12-03-2025 (Kenyan courts write day first)
    re.compile(r"\b(?P<d>\d{1,2})[/.\-](?P<mn>\d{1,2})[/.\-](?P<y>\d{4})\b"),
]

# Phrases that make a date a *next court date* rather than any date mentioned.
_NEXT_DATE_CUE = re.compile(
    r"\b(adjourn(?:ed|s|ment)?|stood over|stand(?:s)? over|mention(?:ed)?|hearing|"
    r"ruling|judgment|judgement|fixed for|set down|next date|"
    # Kiswahili verbs carry subject/tense prefixes (li-me-ahirishwa, li-ta-tajwa),
    # so match stems rather than whole words.
    r"\w*ahirish\w*|\w*tajwa|usikilizaji|hukumu|uamuzi)\b",
    re.I,
)

_PURPOSE = [
    ("ruling", re.compile(r"\b(ruling|uamuzi)\b", re.I)),
    ("judgment", re.compile(r"\b(judg(?:e)?ment|hukumu)\b", re.I)),
    ("mention", re.compile(r"\b(mention|\w*tajwa)\b", re.I)),
    ("hearing", re.compile(r"\b(hearing|usikilizaji)\b", re.I)),
]

ITEM_KINDS = ("outcome", "next_dates", "orders", "directions", "appearances")


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(match: re.Match) -> Optional[date]:
    groups = match.groupdict()
    try:
        day = int(groups["d"])
        year = int(groups["y"])
        month = int(groups["mn"]) if groups.get("mn") else _MONTHS[groups["m"].lower().rstrip(".")]
        return date(year, month, day)
    except (KeyError, ValueError, TypeError):
        return None


def _purpose(text: str) -> Optional[str]:
    for label, pattern in _PURPOSE:
        if pattern.search(text):
            return label
    return None


def _segment_ref(seg: TranscriptSegment) -> dict[str, Any]:
    return {
        "segment_id": str(seg.id),
        "start_ms": seg.start_ms,
        "end_ms": seg.end_ms,
        "speaker": seg.speaker,
    }


def extract_next_dates_rules(segments: list[TranscriptSegment]) -> list[dict[str, Any]]:
    """Deterministic next-date extraction. Only dates in a sentence with a court cue."""
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for seg in segments:
        if seg.redacted or not _NEXT_DATE_CUE.search(seg.text):
            continue
        for pattern in _DATE_PATTERNS:
            for m in pattern.finditer(seg.text):
                parsed = _parse_date(m)
                if not parsed:
                    continue
                key = (str(seg.id), parsed.isoformat())
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    {
                        "kind": "next_date",
                        "date": parsed.isoformat(),
                        "purpose": _purpose(seg.text),
                        "quote": seg.text.strip(),
                        "method": "rules",
                        "grounded": True,
                        **_segment_ref(seg),
                    }
                )
    return found


def ground_quote(quote: str, segments: list[TranscriptSegment]) -> Optional[dict[str, Any]]:
    """Resolve a model quote to the transcript. Exact (normalised) match only.

    Checks single segments first, then adjacent pairs, since a quote can span
    a cue boundary. Returns a segment reference or None.
    """
    q = _norm(quote or "")
    if len(q) < 8:  # too short to be evidence
        return None
    usable = [s for s in segments if not s.redacted]
    for seg in usable:
        if q in _norm(seg.text):
            return _segment_ref(seg)
    for a, b in zip(usable, usable[1:]):
        if q in _norm(f"{a.text} {b.text}"):
            ref = _segment_ref(a)
            ref["end_ms"] = b.end_ms
            ref["spans_segments"] = [str(a.id), str(b.id)]
            return ref
    return None


SYSTEM_PROMPT = """You extract the record of a Kenyan court hearing from its transcript.
The transcript may mix English and Kiswahili. Do not translate quotes.

Return ONLY a JSON object with these keys:
{
  "outcome":     [{"text": "<what happened at this sitting>", "quote": "<verbatim words>"}],
  "next_dates":  [{"date": "<YYYY-MM-DD>", "purpose": "<mention|hearing|ruling|judgment|other>", "quote": "<verbatim words>"}],
  "orders":      [{"text": "<the order the court made>", "quote": "<verbatim words>"}],
  "directions":  [{"text": "<the direction, with deadline if stated>", "quote": "<verbatim words>"}],
  "appearances": [{"name": "<the person's name>", "role": "<judge|magistrate|counsel for X|accused|witness|clerk>", "quote": "<verbatim words>"}]
}

Rules:
- Every <...> is a placeholder: replace it with content from the transcript. Never output the placeholder text.
- "quote" MUST be copied verbatim from ONE transcript line (without the [n] prefix, timestamp, or speaker label).
- Only include items the transcript states. If something is not stated, return an empty list for it.
- Never guess a date. If the year is not stated, omit the item.
"""


def _transcript_block(segments: list[TranscriptSegment]) -> str:
    lines = []
    for i, seg in enumerate(segments):
        mm, ss = divmod(seg.start_ms // 1000, 60)
        who = f"{seg.speaker}: " if seg.speaker else ""
        lines.append(f"[{i}] ({mm:02d}:{ss:02d}) {who}{seg.text}")
    return "\n".join(lines)


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model did not return a JSON object") from None
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model output was not a JSON object")
    return parsed


# Schema wording small models sometimes echo back instead of real content
# (observed with qwen2.5:3b). Matched case-insensitively, brackets ignored.
_PLACEHOLDERS = frozenset(
    {
        "what happened at this sitting",
        "order made by the court",
        "the order the court made",
        "direction to a party, with deadline if stated",
        "the direction, with deadline if stated",
        "person",
        "the person's name",
        "verbatim words",
        "...",
    }
)

_LINE_PREFIX_RE = re.compile(r"^\s*(?:\[\d+\]\s*)?(?:\(\d{1,2}:\d{2}\)\s*)?")
_SPEAKER_PREFIX_RE = re.compile(r"^[^:\n]{1,60}:\s+")


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip().strip("<>").strip().lower() in _PLACEHOLDERS


def _ground_with_prefix_tolerance(quote: str, segments: list[TranscriptSegment]) -> Optional[dict[str, Any]]:
    """Exact grounding, then once more without a copied "[n] (mm:ss) Speaker:" prefix.

    The remainder must still match verbatim, so this never loosens evidence.
    """
    ref = ground_quote(quote, segments)
    if ref is not None:
        return ref
    stripped = _LINE_PREFIX_RE.sub("", quote or "", count=1)
    stripped = _SPEAKER_PREFIX_RE.sub("", stripped, count=1)
    if stripped and stripped != quote:
        return ground_quote(stripped, segments)
    return None


def ground_llm_payload(payload: dict[str, Any], segments: list[TranscriptSegment]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split model items into (grounded, ungrounded). Validates next-date format."""
    grounded: list[dict[str, Any]] = []
    ungrounded: list[dict[str, Any]] = []
    for kind in ITEM_KINDS:
        items = payload.get(kind) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            row = {"kind": kind.rstrip("s") if kind != "outcome" else "outcome", **item, "method": "llm"}
            if kind == "next_dates":
                try:
                    row["date"] = date.fromisoformat(str(item.get("date") or "")).isoformat()
                except ValueError:
                    ungrounded.append({**row, "grounded": False, "reason": "invalid date"})
                    continue
            if any(_is_placeholder(item.get(field)) for field in ("text", "name", "quote")):
                ungrounded.append({**row, "grounded": False, "reason": "model echoed the schema placeholder"})
                continue
            ref = _ground_with_prefix_tolerance(str(item.get("quote") or ""), segments)
            if ref is None:
                ungrounded.append({**row, "grounded": False, "reason": "quote not found in transcript"})
                continue
            grounded.append({**row, "grounded": True, **ref})
    return grounded, ungrounded


async def extract(
    segments: list[TranscriptSegment],
    *,
    use_llm: bool = True,
    provider: Optional[str] = None,
) -> dict[str, Any]:
    """Run rules (+ LLM unless disabled). LLM failure is reported, never hidden."""
    usable = [s for s in segments if not s.redacted and (s.text or "").strip()]
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segments_considered": len(usable),
        "privileged_segments_excluded": len(segments) - len([s for s in segments if not s.redacted]),
        "rules": extract_next_dates_rules(usable),
        "llm": None,
    }
    if not use_llm or not usable:
        return result

    from app.services import ai_mode, ai_runs, generation

    started = time.perf_counter()
    llm: dict[str, Any] = {"status": "error", "items": [], "ungrounded": []}
    provenance: dict[str, Any] = {}
    try:
        text = await generation.complete_text(
            SYSTEM_PROMPT,
            f"Transcript:\n{_transcript_block(usable)}",
            provider,
            task="proceedings",
        )
        if text:
            provenance = generation.last_completion() or {}
        payload = _parse_json_object(text or "")
        items, ungrounded = ground_llm_payload(payload, usable)
        llm.update({"status": "ok", "items": items, "ungrounded": ungrounded})
    except ai_mode.AiModeError as exc:
        llm.update({"status": "blocked_by_ai_mode", "error": str(exc)})
    except Exception as exc:  # noqa: BLE001 — rules output still stands
        # Some exceptions (e.g. httpx timeouts) have an empty message; keep the type.
        reason = f"{type(exc).__name__}: {exc}".rstrip(": ")
        logger.warning("Proceedings LLM extraction failed: %s", reason)
        llm.update({"error": reason[:300]})
    latency_ms = int((time.perf_counter() - started) * 1000)
    llm.update(
        {
            "provider": provenance.get("provider"),
            "model": provenance.get("model"),
            "ai_mode": ai_mode.get_mode(),
            "latency_ms": latency_ms,
        }
    )
    try:
        ai_runs.record(
            task="proceedings",
            provider=str(provenance.get("provider") or "unknown"),
            model_id=str(provenance.get("model") or "unknown"),
            latency_ms=latency_ms,
            status="ok" if llm["status"] == "ok" else "error",
            privileged_lines_excluded=result["privileged_segments_excluded"],
        )
    except Exception:  # noqa: BLE001
        pass
    result["llm"] = llm
    return result
