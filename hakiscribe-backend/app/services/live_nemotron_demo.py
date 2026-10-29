"""Short live Nemotron demo — transcript only, no pre-seeded actions.

Judges click Detect / Generate so Token Factory calls are real and visible.
This is intentionally ~20 lines, not the padded Wanjiru showcase catalog.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

LIVE_NEMOTRON_TITLE = "Live Nemotron demo — Kilimani demand (short)"


def live_nemotron_spec() -> dict[str, Any]:
    """Compact English/Kiswahili intake with privilege, demand, date, research cue."""
    segments = [
        {
            "speaker": "Speaker 1",
            "start_ms": 0,
            "end_ms": 4500,
            "text": (
                "Thanks for coming in, James. This conversation is privileged. "
                "Walk me through the Kilimani slab defect from the beginning."
            ),
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 4600,
            "end_ms": 11000,
            "text": (
                "Sarova Contractors were meant to finish the slab by the fifteenth of June. "
                "By early July there was cracking on the second floor and water near the stair core."
            ),
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 11100,
            "end_ms": 14500,
            "text": "When did your clerk first flag it, and what did Eng. Mutiso say?",
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 14600,
            "end_ms": 21000,
            "text": (
                "Clerk note on the third of July. Mutiso came on the ninth — inadequate curing "
                "and possible under-reinforcement. Remedial estimate is about four point two million."
            ),
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 21100,
            "end_ms": 24500,
            "text": "Did you put Sarova on notice in writing?",
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 24600,
            "end_ms": 32000,
            "text": (
                "Yes — email on the fifth of July, WhatsApp on the eighteenth. "
                "They said they would send an engineer. Hakuna kitu ilifanyika."
            ),
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 32100,
            "end_ms": 36000,
            "text": "Contract sum and what you have paid so far?",
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 36100,
            "end_ms": 43000,
            "text": (
                "Eighteen million shillings. We have paid twelve point six million against "
                "certified works and withheld the balance after the cracking showed up."
            ),
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 43100,
            "end_ms": 49000,
            "text": (
                "I want a formal demand letter before arbitration under clause forty-one. "
                "Twenty-one days from service to respond."
            ),
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 49100,
            "end_ms": 53000,
            "text": "How soon can you diarise a follow-up?",
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 53100,
            "end_ms": 58000,
            "text": (
                "Third of October at ten in the morning in chambers. "
                "Also research briefly whether Kenyan courts treat demand before arbitration as usual practice."
            ),
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 58100,
            "end_ms": 64000,
            "text": (
                "Please keep the bit about my partner's tax position out of anything you write — "
                "that stays between us."
            ),
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 64100,
            "end_ms": 70000,
            "text": (
                "Noted — that stays off the record. The demand letter only uses contract facts, "
                "Mutiso's figures, and the correspondence timeline."
            ),
        },
        {
            "speaker": "Speaker 2",
            "start_ms": 70100,
            "end_ms": 74000,
            "text": "Asante, Naomi. I will send Mutiso's report and the payment schedule this afternoon.",
        },
        {
            "speaker": "Speaker 1",
            "start_ms": 74100,
            "end_ms": 78000,
            "text": "Perfect. Draft goes to you for review before service. Nothing leaves without your approval.",
        },
    ]
    redact_indexes = [
        i
        for i, seg in enumerate(segments)
        if "partner's tax" in seg["text"] or "partner's tax" in seg["text"].lower()
    ]
    flag_payment = next(
        (i for i, seg in enumerate(segments) if "twelve point six" in seg["text"]),
        7,
    )
    flag_deadline = next(
        (i for i, seg in enumerate(segments) if "Twenty-one days" in seg["text"] or "twenty-one days" in seg["text"]),
        8,
    )
    return {
        "title": LIVE_NEMOTRON_TITLE,
        "source": "mic",
        "language_hint": "code-switch",
        "client_name": "Wanjiru Holdings Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "James Wanjiru"},
        "segments": segments,
        "redact_indexes": redact_indexes,
        "flags": [
            {"at_ms": segments[flag_payment]["start_ms"], "label": "Payment withheld — key fact"},
            {"at_ms": segments[flag_deadline]["start_ms"], "label": "Demand deadline"},
        ],
        # Never auto-detect or generate — the judge must trigger live Token Factory calls.
        "generate": False,
    }


def _apply_body(session_id, spec: dict[str, Any]) -> None:
    from app.models.schemas import FlaggedMoment, SessionStatus, TranscriptSegment
    from app.services import storage

    segments = [
        TranscriptSegment(session_id=session_id, **raw)
        for raw in (spec.get("segments") or [])
    ]
    storage.replace_transcript(session_id, segments)
    storage.replace_flags(
        session_id,
        [FlaggedMoment(session_id=session_id, **flag) for flag in (spec.get("flags") or [])],
    )
    storage.relabel_speakers(session_id, spec.get("speakers") or {})
    detail = storage.get_session(session_id)
    if detail:
        for index in spec.get("redact_indexes") or []:
            if 0 <= index < len(detail.transcript):
                storage.update_segment(session_id, detail.transcript[index].id, redacted=True)
    storage.update_session_status(session_id, SessionStatus.ready)
    client = spec.get("client_name")
    if client:
        matter = storage.find_matter_by_client(client)
        if matter is not None:
            storage.link_matter_to_session(session_id, matter.id)


async def ensure_live_nemotron_demo(*, rebuild: bool = False):
    """Materialize the short session with privilege locked and no Action Tray yet.

    Returns ``(detail, created)``. Detect and generate are left to the UI so
    Nebius Token Factory / Tavily calls happen in front of the judge.
    """
    from app.models.schemas import Session, SessionSource
    from app.services import storage

    spec = live_nemotron_spec()
    existing = None
    for item in storage.list_library_sessions():
        if item.title == LIVE_NEMOTRON_TITLE:
            existing = storage.get_session(item.id)
            break

    if existing is not None and not rebuild:
        # If a previous run already detected, still return it — caller can force rebuild.
        return existing, False

    if existing is not None:
        storage.clear_action_pipeline(existing.id)
        _apply_body(existing.id, spec)
        return storage.get_session(existing.id), False

    session = storage.create_session(
        Session(
            title=spec["title"],
            source=SessionSource(spec["source"]),
            language_hint=spec.get("language_hint"),
        )
    )
    _apply_body(session.id, spec)
    detail = storage.get_session(session.id)
    logger.info("Live Nemotron demo session ready id=%s segments=%s", session.id, len(spec["segments"]))
    return detail, True
