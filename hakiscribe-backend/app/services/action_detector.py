"""
Runs one LLM pass over a finalized transcript and returns candidate
"legal artifacts" the user might want generated — this is the Granola-
style action tray, not a single fixed document type.

Uses OpenRouter (already HakiChain's LLM routing layer) so swapping the
underlying model doesn't touch anything outside this file.

Three inputs shape detection beyond the raw transcript:
- Redacted segments are excluded entirely — privilege/off-record control.
- Flagged moments (the no-look 'Flag this moment' button during
  recording) are passed along so the model weighs them as known-important.
- Known matters (existing clients) let the model propose 'add to existing
  matter' instead of always proposing a new one.
"""

import json
import os
import uuid

import httpx

from app.models.schemas import ActionType, DetectedAction, FlaggedMoment, Matter, TranscriptSegment

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DETECTION_MODEL = os.environ.get("DETECTION_MODEL", "openai/gpt-4o")

DETECTION_SYSTEM_PROMPT = """You are reviewing a transcript of a legal \
conversation or proceeding (lawyer-client meeting, court proceeding, \
deposition, etc). Identify concrete follow-up artifacts a legal \
professional would want generated from this conversation.

For each candidate artifact, output an object with:
- "type": one of "draft_document", "calendar_event", "workspace_matter", \
"crm_entry", "private_note", "time_entry"
- "title": short human-readable label, e.g. "Draft: Demand Letter"
- "preview": one sentence grounding it in what was actually said
- "confidence": 0.0-1.0
- "confidence_reason": a short phrase — "Explicitly stated" if the \
transcript said this directly, "Inferred from context" if you're \
reading between the lines
- "source_quote": the short exact phrase from the transcript that most \
directly grounds this artifact (used to let the user jump to that \
moment — keep it under 15 words)
- "extracted_fields": a dict with whatever's needed to generate it:
  - draft_document: {"document_kind": "demand_letter", "parties": [...], \
"key_facts": "..."}
  - calendar_event: {"title": "...", "date": "...", "time": "..."}
  - workspace_matter: {"matter_name": "...", "client": "...", \
"existing_matter_id": "<id or omit if new>"}
  - crm_entry: {"contact_name": "...", "updates": {...}}
  - private_note: {"note_text": "..."}
  - time_entry: {"duration_hours": 0.6, "activity_description": "...", \
"matter_name": "..."}
- "pre_checked": true if this is a high-confidence, clearly-wanted \
artifact; false if it's speculative and the user should opt in

Moments the user explicitly flagged during recording (given below, if \
any) are known-important — weigh them heavily when deciding what to \
surface, even if they're brief.

Known existing clients/matters are given below, if any. If this \
transcript is clearly a follow-up with one of them, use \
"existing_matter_id" in a workspace_matter's extracted_fields instead of \
proposing a brand new matter for the same client.

For time_entry, estimate a reasonable duration only if the conversation \
gives you a basis (e.g. total transcript duration, or an explicit mention) \
— don't invent a number with no grounding.

Only surface things actually supported by the transcript — do not \
invent parties, dates, or facts that weren't mentioned. Return ONLY a \
JSON array of these objects, nothing else."""


def _build_context_block(flags: list[FlaggedMoment], matters: list[Matter]) -> str:
    parts = []
    if flags:
        flag_lines = "\n".join(f"- at {f.at_ms}ms" + (f": {f.label}" if f.label else "") for f in flags)
        parts.append(f"User-flagged moments:\n{flag_lines}")
    if matters:
        matter_lines = "\n".join(f"- id={m.id}, client={m.client_name}, matter={m.matter_name}" for m in matters)
        parts.append(f"Known existing clients/matters:\n{matter_lines}")
    return "\n\n".join(parts)


def _actions_from_raw(session_id: uuid.UUID, usable_segments: list[TranscriptSegment], raw_actions: list[dict]) -> list[DetectedAction]:
    actions = []
    for raw in raw_actions:
        try:
            action_type = ActionType(raw["type"])
        except (KeyError, ValueError):
            continue
        source_segment_id = _find_source_segment(usable_segments, raw.get("source_quote"))
        actions.append(
            DetectedAction(
                session_id=session_id,
                type=action_type,
                title=raw.get("title") or action_type.value.replace("_", " ").title(),
                preview=raw.get("preview") or "",
                confidence=float(raw.get("confidence", 0.5)),
                confidence_reason=raw.get("confidence_reason"),
                source_segment_id=source_segment_id,
                extracted_fields=raw.get("extracted_fields", {}),
                pre_checked=bool(raw.get("pre_checked", True)),
            )
        )
    return actions


def _detect_heuristic(
    session_id: uuid.UUID,
    usable_segments: list[TranscriptSegment],
    flags: list[FlaggedMoment],
    known_matters: list[Matter],
    session_title: str | None,
) -> list[DetectedAction]:
    """Populate the Action Tray from the transcript when no LLM key is set."""
    text = " ".join(segment.text for segment in usable_segments).lower()
    speakers = []
    for segment in usable_segments:
        if segment.speaker and segment.speaker not in speakers:
            speakers.append(segment.speaker)
    first_line = usable_segments[0].text.strip() if usable_segments else ""
    quote = first_line[:80] if first_line else (session_title or "session")
    client = speakers[0] if speakers else "Client"
    matter_name = session_title or f"{client} matter"
    existing = next((matter for matter in known_matters if client.lower() in matter.client_name.lower()), None)
    hours = 0.3
    if usable_segments:
        span_ms = max(segment.end_ms for segment in usable_segments) - min(segment.start_ms for segment in usable_segments)
        hours = max(round(span_ms / 3_600_000, 2), 0.1)

    legal_hits = any(word in text for word in ("demand", "letter", "agreement", "contract", "affidavit", "notice", "brief", "undertaking", "memo"))
    calendar_hits = any(
        word in text
        for word in (
            "monday", "tuesday", "wednesday", "thursday", "friday", "tomorrow",
            "next week", "follow up", "follow-up", "hearing", "mention", "o'clock", "am", "pm",
        )
    )

    raw: list[dict] = [
        {
            "type": "workspace_matter",
            "title": f"Matter: {matter_name}",
            "preview": f"Open or link a workspace matter for {client}.",
            "confidence": 0.82,
            "confidence_reason": "Inferred from context",
            "source_quote": quote,
            "extracted_fields": {
                "matter_name": matter_name,
                "client": client,
                **({"existing_matter_id": str(existing.id)} if existing else {}),
            },
            "pre_checked": True,
        },
        {
            "type": "draft_document",
            "title": "Draft: Demand Letter" if "demand" in text else "Draft: Legal Memo",
            "preview": first_line or "Prepare a working draft from the verified record.",
            "confidence": 0.78 if legal_hits else 0.64,
            "confidence_reason": "Explicitly stated" if legal_hits else "Inferred from context",
            "source_quote": quote,
            "extracted_fields": {
                "document_kind": "demand_letter" if "demand" in text else "legal_memo",
                "parties": speakers or [client],
                "key_facts": first_line or matter_name,
            },
            "pre_checked": True,
        },
        {
            "type": "time_entry",
            "title": "Time entry for this session",
            "preview": f"Bill {hours} hours against {matter_name}.",
            "confidence": 0.8,
            "confidence_reason": "Inferred from context",
            "source_quote": quote,
            "extracted_fields": {
                "duration_hours": hours,
                "activity_description": first_line or f"Client conference regarding {matter_name}",
                "matter_name": matter_name,
            },
            "pre_checked": True,
        },
    ]
    if speakers:
        raw.append(
            {
                "type": "crm_entry",
                "title": f"Update contact: {client}",
                "preview": f"Keep {client} current from this conversation.",
                "confidence": 0.7,
                "confidence_reason": "Inferred from context",
                "source_quote": quote,
                "extracted_fields": {"contact_name": client, "updates": {"last_session": session_title or matter_name}},
                "pre_checked": True,
            }
        )
    if calendar_hits or flags:
        raw.append(
            {
                "type": "calendar_event",
                "title": "Follow-up from this session",
                "preview": flags[0].label if flags and flags[0].label else "Schedule the follow-up mentioned on the record.",
                "confidence": 0.74 if calendar_hits else 0.6,
                "confidence_reason": "Explicitly stated" if calendar_hits else "Inferred from context",
                "source_quote": quote,
                "extracted_fields": {"title": "Follow-up from this session", "date": None, "time": "09:00"},
                "pre_checked": bool(calendar_hits or flags),
            }
        )
    if flags:
        label = flags[0].label or "Flagged moment"
        raw.append(
            {
                "type": "private_note",
                "title": f"Note: {label}",
                "preview": "Capture the moment the user flagged during recording.",
                "confidence": 0.9,
                "confidence_reason": "Explicitly stated",
                "source_quote": quote,
                "extracted_fields": {"note_text": label},
                "pre_checked": True,
            }
        )
    return _actions_from_raw(session_id, usable_segments, raw)


async def detect_actions(
    session_id: uuid.UUID,
    transcript: list[TranscriptSegment],
    flags: list[FlaggedMoment] | None = None,
    known_matters: list[Matter] | None = None,
    session_title: str | None = None,
) -> list[DetectedAction]:
    usable_segments = [seg for seg in transcript if not seg.redacted]
    flags = flags or []
    known_matters = known_matters or []

    transcript_text = "\n".join(
        f"[{seg.speaker or 'unknown'}] ({seg.id}) {seg.text}" for seg in usable_segments
    )
    context_block = _build_context_block(flags, known_matters)
    user_content = f"{context_block}\n\nTranscript:\n{transcript_text}" if context_block else transcript_text

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    OPENROUTER_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": DETECTION_MODEL,
                        "messages": [
                            {"role": "system", "content": DETECTION_SYSTEM_PROMPT},
                            {"role": "user", "content": user_content},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]

            content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            raw_actions = json.loads(content)
            actions = _actions_from_raw(session_id, usable_segments, raw_actions)
            if actions:
                return actions
        except Exception:  # noqa: BLE001 — tray still populates from the transcript
            pass

    return _detect_heuristic(session_id, usable_segments, flags, known_matters, session_title)


def _find_source_segment(segments: list[TranscriptSegment], quote: str | None) -> uuid.UUID | None:
    if not quote:
        return None
    quote_lower = quote.lower()
    for seg in segments:
        if quote_lower in seg.text.lower():
            return seg.id
    return None
