"""Build a completed Kenyan client-meeting session in-process.

Judges can open a finished Action Tray without a microphone. If a
Wanjiru showcase already exists (after seed_demo or a prior click),
reuse it so Render spin-down is the only reason we rebuild — unless
Ambiguous is configured and the cached results never landed there.
"""

from __future__ import annotations

import os

from app.models.schemas import (
    ActionResult,
    ActionType,
    DetectedAction,
    FlaggedMoment,
    Session,
    SessionSource,
    SessionStatus,
    TranscriptSegment,
)
from app.services import action_detector, action_executor, enrichment, storage, trigger_client

SHOWCASE_TITLE = "Client meeting — Wanjiru Holdings, defective works at Kilimani site"


def _seg(speaker: str, text: str, start_s: float, dur_s: float = 6) -> dict:
    return {
        "speaker": speaker,
        "text": text,
        "start_ms": int(start_s * 1000),
        "end_ms": int((start_s + dur_s) * 1000),
        "confidence": 0.94,
    }


SHOWCASE_SEGMENTS = [
    _seg("Speaker 1", "Thanks for coming in, James. Before we start — this conversation is privileged. Take me through what happened at the Kilimani site.", 0, 9),
    _seg("Speaker 2", "Sarova Contractors were meant to complete the slab works by the fifteenth of June. By July the slab had visible cracking on the second floor.", 9, 11),
    _seg("Speaker 1", "Did you raise it with them in writing?", 20, 4),
    _seg("Speaker 2", "Yes, twice. Email on the second of July, then a WhatsApp on the eighteenth. They said they would send an engineer, hakuna kitu ilifanyika.", 24, 12),
    _seg("Speaker 1", "And the contract sum? What has been paid so far?", 36, 5),
    _seg("Speaker 2", "Contract was eighteen million shillings. We have paid twelve point six million. We withheld the balance after the cracking.", 41, 11),
    _seg("Speaker 2", "The structural engineer, Eng. Mutiso, says remedial works will cost about four point two million.", 52, 9),
    _seg("Speaker 1", "Good. That gives us a quantified loss. I want to send a formal demand letter to Sarova Contractors before we consider arbitration under clause 41.", 61, 13),
    _seg("Speaker 2", "How long do they get?", 74, 3),
    _seg("Speaker 1", "Twenty-one days. If they don't respond we file a notice of arbitration. Let's also diarise a follow-up meeting on the third of October at ten in the morning.", 77, 14),
    _seg("Speaker 2", "That works. Also, please keep the bit about my partner's tax position out of anything you write.", 91, 8),
    _seg("Speaker 1", "Noted — that stays off the record. I'll get the demand letter to you for review by Friday.", 99, 8),
]


def find_existing_showcase():
    for item in storage.list_library_sessions():
        if item.title == SHOWCASE_TITLE and (item.generated_types or item.status.value in {"ready", "exported"}):
            detail = storage.get_session(item.id)
            if detail and (detail.action_results or detail.detected_actions):
                return detail
    return None


def _missing_workspace_mirror(detail) -> bool:
    if not os.environ.get("AMBIGUOUS_API_KEY"):
        return False
    for item in detail.action_results or []:
        payload = item.result or {}
        if payload.get("ambiguous_document_id") or payload.get("ambiguous_event_id") or payload.get("ambiguous_deal_id"):
            return False
    return any(
        item.type in {ActionType.draft_document, ActionType.calendar_event, ActionType.workspace_matter}
        for item in (*(detail.action_results or []), *(detail.detected_actions or []))
    )


async def _detect(detail):
    payload = {
        "session_id": str(detail.id),
        "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
        "flags": [flag.model_dump(mode="json") for flag in detail.flagged_moments],
        "known_matters": [matter.model_dump(mode="json") for matter in storage.list_matters()],
        "session_title": detail.title,
    }
    trigger_output = await trigger_client.trigger_and_wait("detect-actions", payload)
    if trigger_output is not None:
        return [DetectedAction(**item) for item in trigger_output]
    return await action_detector.detect_actions(
        detail.id,
        detail.transcript,
        flags=detail.flagged_moments,
        known_matters=storage.list_matters(),
        session_title=detail.title,
    )


async def _generate(detail, actions):
    payload = {
        "actions": [action.model_dump(mode="json") for action in actions],
        "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
    }
    trigger_output = await trigger_client.trigger_and_wait("generate-actions", payload, timeout_s=240.0)
    if trigger_output is not None:
        return [ActionResult(**item) for item in trigger_output]
    return await action_executor.execute_actions(actions, transcript=detail.transcript)


async def ensure_showcase(rebuild: bool = False):
    existing = None if rebuild else find_existing_showcase()
    if existing is not None and _missing_workspace_mirror(existing):
        checked = [action for action in existing.detected_actions if action.pre_checked] or existing.detected_actions[:3]
        if checked:
            results = await _generate(existing, checked)
            storage.upsert_action_results(existing.id, results)
            storage.update_session_status(existing.id, SessionStatus.exported)
            return storage.get_session(existing.id), False
    if existing is not None:
        return existing, False

    session = storage.create_session(
        Session(
            title=SHOWCASE_TITLE,
            source=SessionSource.omi,
            language_hint="code-switch",
        )
    )
    for raw in SHOWCASE_SEGMENTS:
        storage.append_segment(
            session.id,
            TranscriptSegment(session_id=session.id, **raw),
        )
    storage.add_flag(session.id, FlaggedMoment(session_id=session.id, at_ms=192000, label="Payment withheld — key fact"))
    storage.add_flag(session.id, FlaggedMoment(session_id=session.id, at_ms=356000, label="Deadline for demand letter"))
    storage.relabel_speakers(session.id, {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "James Wanjiru"})

    detail = storage.get_session(session.id)
    if detail and len(detail.transcript) > 10:
        storage.update_segment(session.id, detail.transcript[10].id, redacted=True)

    storage.update_session_status(session.id, SessionStatus.ready)
    detail = storage.get_session(session.id)
    if detail is None:
        return None, True
    actions = await _detect(detail)
    actions = await enrichment.enrich_with_exa(actions)
    storage.set_detected_actions(session.id, actions)
    checked = [action for action in actions if action.pre_checked] or actions[:3]
    if checked:
        results = await _generate(detail, checked)
        storage.upsert_action_results(session.id, results)
        storage.update_session_status(session.id, SessionStatus.exported)
    return storage.get_session(session.id), True
