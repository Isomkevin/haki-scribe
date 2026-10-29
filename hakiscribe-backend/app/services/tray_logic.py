"""Pure tray / privilege helpers — no I/O, unit-testable.

Maps the reference ``tray.ts`` trust model onto HakiScribe's field names:
privileged lines use ``redacted=True``; citations resolve via ``source_quote``
to a real non-redacted segment id.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Iterable, Sequence

# Action types used by the product Action Tray (schemas.ActionType values).
ACTION_TYPES = frozenset(
    {
        "draft_document",
        "calendar_event",
        "workspace_matter",
        "crm_entry",
        "private_note",
        "time_entry",
        "legal_research",
        "web_search",
        "llm_task",
    }
)


def visible_segments(segments: Sequence[Any]) -> list[Any]:
    """Segments that may be sent to a model (not privileged / off-record)."""
    return [s for s in segments if not getattr(s, "redacted", False)]


def privileged_count(segments: Sequence[Any]) -> int:
    return sum(1 for s in segments if getattr(s, "redacted", False))


def build_transcript_block(
    segments: Sequence[Any],
    *,
    flagged_ids: Iterable[Any] | None = None,
) -> str:
    """Numbered transcript block the model reads. Privileged lines are absent."""
    flagged = set(flagged_ids or [])
    lines: list[str] = []
    for seg in visible_segments(segments):
        speaker = getattr(seg, "speaker", None) or "unknown"
        seg_id = getattr(seg, "id", "")
        flag = "(FLAGGED) " if seg_id in flagged else ""
        text = getattr(seg, "text", "") or ""
        lines.append(f"[{speaker}] ({seg_id}) {flag}{text}")
    return "\n".join(lines)


def clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return default
    if not (conf == conf):  # NaN
        return default
    return max(0.0, min(1.0, conf))


def extract_json(text: str) -> Any:
    """Parse JSON from model output that may contain <think> blocks or fences."""
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE).strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    # Prefer object, then array.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(open_ch), cleaned.rfind(close_ch)
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object in model output")


def find_source_segment(segments: Sequence[Any], quote: str | None) -> uuid.UUID | None:
    """Resolve a source quote to a non-privileged segment id, or None."""
    if not quote:
        return None
    quote_lower = str(quote).lower().strip()
    if not quote_lower:
        return None
    usable = visible_segments(segments)
    for seg in usable:
        text = (getattr(seg, "text", "") or "").lower()
        if quote_lower in text:
            return getattr(seg, "id", None)
    return None


def validate_raw_actions(
    raw_actions: list[dict],
    usable_segments: Sequence[Any],
    *,
    session_id: uuid.UUID | None = None,
) -> tuple[list[dict], list[dict]]:
    """Validate model tray output.

    Returns ``(kept, dropped)`` where kept items are dicts ready for
    DetectedAction construction. Drops unknown types, missing titles,
    missing non-privileged citations; clamps confidence; dedupes type+title.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    allowed_ids = {getattr(s, "id", None) for s in visible_segments(usable_segments)}

    for index, raw in enumerate(raw_actions):
        if not isinstance(raw, dict):
            dropped.append({"index": index, "reason": "not an object"})
            continue
        action_type = str(raw.get("type") or "").strip()
        if action_type not in ACTION_TYPES:
            dropped.append({"index": index, "reason": f"unknown type: {action_type}"})
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            dropped.append({"index": index, "reason": "missing title"})
            continue

        source_segment_id = find_source_segment(usable_segments, raw.get("source_quote"))
        # Also accept an explicit source_segment_id if it is non-privileged.
        if source_segment_id is None:
            explicit = raw.get("source_segment_id")
            if explicit is not None:
                try:
                    candidate = uuid.UUID(str(explicit))
                except (TypeError, ValueError):
                    candidate = None
                if candidate in allowed_ids:
                    source_segment_id = candidate
        if source_segment_id is None:
            dropped.append({"index": index, "reason": "no valid non-privileged source line"})
            continue

        key = (action_type, title.lower())
        if key in seen:
            dropped.append({"index": index, "reason": "duplicate"})
            continue
        seen.add(key)

        fields = raw.get("extracted_fields")
        if not isinstance(fields, dict):
            fields = {}

        kept.append(
            {
                "session_id": session_id,
                "type": action_type,
                "title": title,
                "preview": str(raw.get("preview") or ""),
                "confidence": clamp_confidence(raw.get("confidence", 0.5)),
                "confidence_reason": raw.get("confidence_reason"),
                "source_segment_id": source_segment_id,
                "extracted_fields": fields,
                "pre_checked": bool(raw.get("pre_checked", True)),
            }
        )
    return kept, dropped
