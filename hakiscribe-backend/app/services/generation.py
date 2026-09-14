"""
Transcript-grounded generation models for Action Tray cards.

Each model turns a DetectedAction plus the verified (non-redacted)
transcript into real text the frontend can render: a legal draft, a
calendar event with description + .ics, or a billable time narrative.
OpenRouter is used when OPENROUTER_API_KEY is set; otherwise the same
shape is produced locally from the transcript so Generate never returns
empty placeholders.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta

import httpx

from app.services import documents
from app.models.schemas import (
    CalendarEventResult,
    DetectedAction,
    DraftDocumentResult,
    TimeEntryResult,
    TranscriptSegment,
)

from app.integrations import llm_client
from app.services.integrations import openrouter_headers

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DRAFTING_MODEL = os.environ.get("DRAFTING_MODEL", "openai/gpt-4o")


def usable_transcript(transcript: list[TranscriptSegment] | None) -> list[TranscriptSegment]:
    return [segment for segment in (transcript or []) if not segment.redacted and segment.text.strip()]


def format_transcript(transcript: list[TranscriptSegment] | None) -> str:
    lines = []
    for segment in usable_transcript(transcript):
        speaker = segment.speaker or "Speaker"
        lines.append(f"{speaker}: {segment.text.strip()}")
    return "\n".join(lines)


def speakers_from_transcript(transcript: list[TranscriptSegment] | None) -> list[str]:
    names: list[str] = []
    for segment in usable_transcript(transcript):
        if segment.speaker and segment.speaker not in names:
            names.append(segment.speaker)
    return names


def _duration_hours(transcript: list[TranscriptSegment] | None, fallback: float | None = None) -> float:
    if fallback not in (None, "", 0, "0"):
        try:
            return round(float(fallback), 2)
        except (TypeError, ValueError):
            pass
    segments = usable_transcript(transcript)
    if not segments:
        return 0.3
    span_ms = max(segment.end_ms for segment in segments) - min(segment.start_ms for segment in segments)
    hours = max(span_ms / 3_600_000, 0.1)
    return round(hours, 2)


async def complete_text(system_prompt: str, user_prompt: str) -> str | None:
    api_key = llm_client.api_key()
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {api_key}", **openrouter_headers()},
                json={
                    "model": DRAFTING_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return (content or "").strip() or None
    except Exception:  # noqa: BLE001 — fall back to transcript-composed text
        return None


class DraftDocumentModel:
    """Drafts a real, filing-shaped legal document from the verified record.

    The document is composed from facts extracted out of the transcript
    (parties, sums, dates, statutes, title numbers, deadlines) into the
    correct Kenyan instrument for the detected kind. When a drafting model
    is configured it drafts on top of those same extracted facts; when it
    isn't, the composed instrument IS the draft — never a placeholder.
    """

    SYSTEM_PROMPT = (
        "You are a Kenyan advocate drafting a real legal instrument for filing or "
        "service. Draft the full document in correct Kenyan form and legal register: "
        "proper heading (REPUBLIC OF KENYA / court / cause number for pleadings, "
        "letterhead and RE: line for correspondence), numbered paragraphs, prayers or "
        "a demand with a stated compliance period, and a signature/jurat block. Cite "
        "only statutes actually mentioned in the record. Use ONLY facts supported by "
        "the transcript and the extracted-facts list — never invent a party, figure, "
        "date or authority. Anything not on the record must appear as a bracketed "
        "placeholder such as [ADDRESS] or [DATE]. Output only the document text."
    )

    async def generate(self, action: DetectedAction, transcript: list[TranscriptSegment] | None) -> DraftDocumentResult:
        fields = action.extracted_fields
        record = format_transcript(transcript)
        kind = documents.normalise_kind(
            fields.get("document_kind"),
            f"{action.title} {action.preview} {record}",
        )
        parties = fields.get("parties") or speakers_from_transcript(transcript)
        if isinstance(parties, list):
            parties_text = ", ".join(str(item) for item in parties if item)
        else:
            parties_text = str(parties)
        key_facts = str(fields.get("key_facts") or action.preview)
        facts = documents.extract_facts(transcript)

        prompt = (
            f"Document to draft: {documents.KIND_TITLES.get(kind, kind)}\n"
            f"Matter/title: {action.title}\n"
            f"Parties: {parties_text or 'not specified'}\n"
            f"Key facts: {key_facts}\n\n"
            f"Checkable facts extracted from the record:\n{documents.facts_brief(facts) or '(none)'}\n\n"
            f"Verified (non-redacted) transcript:\n{record or '(no non-redacted lines)'}\n\n"
            "Draft the complete document now."
        )
        document_text = await complete_text(self.SYSTEM_PROMPT, prompt)
        if not document_text or len(document_text) < 400:
            document_text = documents.compose_document(kind, action, transcript)
        document_text += documents.compliance_footer(kind)

        return DraftDocumentResult(
            document_text=document_text,
            document_kind=kind,
            source="transcript",
        )



class CalendarEventModel:
    """Builds a follow-up event with real description text and a downloadable .ics."""

    SYSTEM_PROMPT = (
        "Write a concise calendar event description (3-6 sentences) for a legal "
        "follow-up. Use only facts from the transcript. Output only the description."
    )

    async def generate(self, action: DetectedAction, transcript: list[TranscriptSegment] | None) -> CalendarEventResult:
        fields = action.extracted_fields
        title = str(fields.get("title") or action.title)
        start, end = self._parse_window(fields)
        attendees = speakers_from_transcript(transcript)
        record = format_transcript(transcript)
        description = await complete_text(
            self.SYSTEM_PROMPT,
            f"Event title: {title}\nPreview: {action.preview}\n\nTranscript:\n{record or action.preview}",
        )
        if not description:
            who = f" Attendees on the record: {', '.join(attendees)}." if attendees else ""
            excerpt = record if record else action.preview
            description = (
                f"{title}. {action.preview}{who}\n\n"
                f"Source conversation:\n{excerpt}"
            )

        ics = self._ics(title, start, end, description, attendees)
        return CalendarEventResult(
            title=title,
            start=start.isoformat(),
            end=end.isoformat(),
            description=description,
            attendees=attendees,
            ics=ics,
        )

    def _parse_window(self, fields: dict) -> tuple[datetime, datetime]:
        raw_date = fields.get("date")
        raw_time = fields.get("time") or "09:00"
        start = None
        if raw_date:
            time_part = str(raw_time)
            if re.fullmatch(r"\d{1,2}", time_part):
                time_part = f"{int(time_part):02d}:00"
            if re.fullmatch(r"\d{1,2}:\d{2}", time_part):
                time_part = f"{time_part}:00" if len(time_part.split(':')[0]) == 2 else time_part
            candidates = [
                f"{raw_date}T{raw_time}",
                f"{raw_date}T{time_part}",
                str(raw_date),
            ]
            for candidate in candidates:
                try:
                    start = datetime.fromisoformat(str(candidate).replace("Z", ""))
                    break
                except (ValueError, TypeError):
                    continue
        if start is None:
            start = datetime.utcnow() + timedelta(days=7)
            start = start.replace(hour=9, minute=0, second=0, microsecond=0)
        return start, start + timedelta(hours=1)

    def _ics(self, title: str, start: datetime, end: datetime, description: str, attendees: list[str]) -> str:
        escaped = description.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//HakiScribe//EN",
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{escaped}",
        ]
        for name in attendees:
            lines.append(f"ATTENDEE;CN={name}:MAILTO:unknown@example.com")
        lines.extend(["END:VEVENT", "END:VCALENDAR"])
        return "\n".join(lines)


class TimeEntryModel:
    """Writes a billable narrative grounded in the conversation length and record."""

    SYSTEM_PROMPT = (
        "Write a professional billable-time narrative (4-8 sentences) for a legal "
        "time entry. Use only the transcript. Output only the narrative."
    )

    async def generate(self, action: DetectedAction, transcript: list[TranscriptSegment] | None) -> TimeEntryResult:
        fields = action.extracted_fields
        hours = _duration_hours(transcript, fields.get("duration_hours"))
        matter_name = fields.get("matter_name")
        record = format_transcript(transcript)
        seed = str(fields.get("activity_description") or action.preview)
        narrative = await complete_text(
            self.SYSTEM_PROMPT,
            f"Matter: {matter_name or 'unspecified'}\nDuration hours: {hours}\n"
            f"Activity: {seed}\n\nTranscript:\n{record or seed}",
        )
        if not narrative:
            speakers = speakers_from_transcript(transcript)
            who = f" with {', '.join(speakers)}" if speakers else ""
            narrative = (
                f"Billable time of {hours} hour{'s' if hours != 1 else ''}{who} "
                f"regarding {matter_name or 'the matter discussed on the record'}. {seed} "
                "Work included reviewing the facts as stated, identifying follow-up "
                "obligations, and capturing the conversation for the file.\n\n"
                f"Record:\n{record or seed}"
            )

        return TimeEntryResult(
            duration_hours=hours,
            activity_description=seed,
            narrative=narrative,
            matter_name=matter_name,
            billable=True,
        )


draft_document_model = DraftDocumentModel()
calendar_event_model = CalendarEventModel()
time_entry_model = TimeEntryModel()
