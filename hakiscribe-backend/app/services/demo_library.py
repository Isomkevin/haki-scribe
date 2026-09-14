"""Idempotent Kenyan demo library for the live desk.

The published app only used to build the Wanjiru judge showcase. Render
spin-down then left that one session as the entire library. This module
materializes every seed matter and session by title, then finishes
detect/generate in the background so a page load is not blocked.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from app.models.schemas import (
    ActionResult,
    ActionType,
    DetectedAction,
    FlaggedMoment,
    Matter,
    Session,
    SessionLibraryItem,
    SessionSource,
    SessionStatus,
    TranscriptSegment,
)
from app.services import action_detector, action_executor, enrichment, storage, trigger_client
from app.services.demo_catalog import MATTERS, SESSIONS, SHOWCASE_TITLE

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_complete_task: asyncio.Task | None = None


def expected_titles() -> list[str]:
    return [spec["title"] for spec in SESSIONS]


def find_session_by_title(title: str):
    for item in storage.list_library_sessions():
        if item.title == title:
            return storage.get_session(item.id)
    return None


def _ensure_matters() -> int:
    created = 0
    known = {matter.matter_name for matter in storage.list_matters()}
    for spec in MATTERS:
        if spec["matter_name"] in known:
            continue
        storage.create_matter(Matter(client_name=spec["client_name"], matter_name=spec["matter_name"]))
        known.add(spec["matter_name"])
        created += 1
    return created


def _link_matter(session_id, client_name: str | None) -> None:
    if not client_name:
        return
    matter = storage.find_matter_by_client(client_name)
    if matter is not None:
        storage.link_matter_to_session(session_id, matter.id)


def _materialize(spec: dict[str, Any]):
    session = storage.create_session(
        Session(
            title=spec["title"],
            source=SessionSource(spec["source"]),
            language_hint=spec.get("language_hint"),
        )
    )
    for raw in spec["segments"]:
        storage.append_segment(session.id, TranscriptSegment(session_id=session.id, **raw))
    for flag in spec.get("flags") or []:
        storage.add_flag(session.id, FlaggedMoment(session_id=session.id, **flag))
    storage.relabel_speakers(session.id, spec.get("speakers") or {})
    detail = storage.get_session(session.id)
    if detail:
        for index in spec.get("redact_indexes") or []:
            if index < len(detail.transcript):
                storage.update_segment(session.id, detail.transcript[index].id, redacted=True)
    storage.update_session_status(session.id, SessionStatus.ready)
    _link_matter(session.id, spec.get("client_name"))
    return storage.get_session(session.id)


def _ensure_records() -> tuple[int, int]:
    _ensure_matters()
    created = 0
    reused = 0
    for spec in SESSIONS:
        existing = find_session_by_title(spec["title"])
        if existing is not None:
            _link_matter(existing.id, spec.get("client_name"))
            reused += 1
            continue
        _materialize(spec)
        created += 1
    return created, reused


def missing_workspace_mirror(detail) -> bool:
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


async def detect(detail):
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


async def generate(detail, actions):
    payload = {
        "actions": [action.model_dump(mode="json") for action in actions],
        "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
    }
    trigger_output = await trigger_client.trigger_and_wait("generate-actions", payload, timeout_s=240.0)
    if trigger_output is not None:
        return [ActionResult(**item) for item in trigger_output]
    return await action_executor.execute_actions(actions, transcript=detail.transcript)


async def complete_session(detail, *, generate_results: bool) -> None:
    if not detail.detected_actions:
        actions = await detect(detail)
        actions = await enrichment.enrich_with_exa(actions)
        storage.set_detected_actions(detail.id, actions)
        detail = storage.get_session(detail.id) or detail
    else:
        actions = detail.detected_actions
    if generate_results and (not detail.action_results or missing_workspace_mirror(detail)):
        checked = [action for action in actions if action.pre_checked] or actions[:3]
        if checked:
            results = await generate(detail, checked)
            storage.upsert_action_results(detail.id, results)
            storage.update_session_status(detail.id, SessionStatus.exported)


async def _complete_pending() -> None:
    for spec in SESSIONS:
        detail = find_session_by_title(spec["title"])
        if detail is None:
            continue
        try:
            await complete_session(detail, generate_results=bool(spec.get("generate")))
        except Exception:
            logger.exception("Could not finish demo session %s", spec["title"])


def schedule_completion() -> bool:
    global _complete_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    if _complete_task is not None and not _complete_task.done():
        return True
    _complete_task = loop.create_task(_complete_pending())
    return True


def _summary(created: int, reused: int, completing: bool) -> dict[str, Any]:
    return {
        "created": created,
        "reused": reused,
        "completing": completing,
        "sessions": storage.list_library_sessions(),
    }


async def sync_demo_library() -> dict[str, Any]:
    async with _lock:
        created, reused = _ensure_records()
    completing = schedule_completion()
    return _summary(created, reused, completing)


async def bootstrap_demo_library() -> None:
    try:
        result = await sync_demo_library()
        logger.info(
            "Demo library ready: created=%s reused=%s",
            result["created"],
            result["reused"],
        )
        if _complete_task is not None:
            await _complete_task
    except Exception:
        logger.exception("Demo library bootstrap failed")


async def ensure_showcase(rebuild: bool = False):
    spec = next(item for item in SESSIONS if item["title"] == SHOWCASE_TITLE)
    async with _lock:
        _ensure_matters()
        existing = None if rebuild else find_session_by_title(SHOWCASE_TITLE)
        if existing is not None and (existing.action_results or existing.detected_actions):
            if missing_workspace_mirror(existing):
                await complete_session(existing, generate_results=True)
                return storage.get_session(existing.id), False
            return existing, False
        if existing is None:
            existing = _materialize(spec)
        if existing is None:
            return None, True
        await complete_session(existing, generate_results=True)
        return storage.get_session(existing.id), True


def library_items() -> list[SessionLibraryItem]:
    return storage.list_library_sessions()
