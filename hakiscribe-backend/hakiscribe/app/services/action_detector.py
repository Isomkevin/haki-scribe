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


async def detect_actions(
    session_id: uuid.UUID,
    transcript: list[TranscriptSegment],
    flags: list[FlaggedMoment] | None = None,
    known_matters: list[Matter] | None = None,
) -> list[DetectedAction]:
    usable_segments = [seg for seg in transcript if not seg.redacted]

    transcript_text = "\n".join(
        f"[{seg.speaker or 'unknown'}] ({seg.id}) {seg.text}" for seg in usable_segments
    )
    context_block = _build_context_block(flags or [], known_matters or [])
    user_content = f"{context_block}\n\nTranscript:\n{transcript_text}" if context_block else transcript_text

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
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

    # Models sometimes wrap JSON in a code fence despite instructions.
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    raw_actions = json.loads(content)

    actions = []
    for raw in raw_actions:
        source_segment_id = _find_source_segment(usable_segments, raw.get("source_quote"))
        actions.append(
            DetectedAction(
                session_id=session_id,
                type=ActionType(raw["type"]),
                title=raw["title"],
                preview=raw["preview"],
                confidence=float(raw.get("confidence", 0.5)),
                confidence_reason=raw.get("confidence_reason"),
                source_segment_id=source_segment_id,
                extracted_fields=raw.get("extracted_fields", {}),
                pre_checked=bool(raw.get("pre_checked", True)),
            )
        )
    return actions


def _find_source_segment(segments: list[TranscriptSegment], quote: str | None) -> uuid.UUID | None:
    if not quote:
        return None
    quote_lower = quote.lower()
    for seg in segments:
        if quote_lower in seg.text.lower():
            return seg.id
    return None
