"""Tenant-backed action detection and drafting; never reads demo storage."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.schemas import ActionResult, ActionStatus, ActionType, AskRequest, DetectedAction, GenerateActionsRequest, SessionStatus
from app.services import action_detector, action_executor, enrichment
from app.services.production_auth import require_csrf
from app.services.tenant_context import production_client, require_organisation, require_session_access
from app.routers.production_sessions import append_record, session_detail

router = APIRouter()


@router.post("/{session_id}/detect", response_model=list[DetectedAction])
async def detect_actions(session_id: uuid.UUID, force: bool = Query(default=False), context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    detail = session_detail(client, row)
    if not detail.transcript:
        raise HTTPException(status_code=400, detail="Session has no transcript yet")
    if detail.detected_actions and not force:
        return detail.detected_actions
    actions = await action_detector.detect_actions(session_id, detail.transcript, flags=detail.flagged_moments, known_matters=[], session_title=detail.title)
    actions = await enrichment.enrich_with_exa(actions)
    for action in actions:
        append_record(client, session_id, user.id, "action", action.model_dump(mode="json"))
    client.table("haki_sessions").update({"status": SessionStatus.ready.value}).eq("id", str(session_id)).execute()
    return actions


@router.get("/{session_id}/actions", response_model=list[DetectedAction])
async def list_actions(session_id: uuid.UUID, context=Depends(require_organisation)):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    return session_detail(client, row).detected_actions


@router.post("/{session_id}/actions/{action_id}/dismiss", response_model=DetectedAction)
async def dismiss_action(session_id: uuid.UUID, action_id: uuid.UUID, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    action = next((item for item in session_detail(client, row).detected_actions if item.id == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    action.status = ActionStatus.dismissed
    append_record(client, session_id, user.id, "action", action.model_dump(mode="json"))
    return action


@router.post("/{session_id}/generate", response_model=list[ActionResult])
async def generate_actions(session_id: uuid.UUID, payload: GenerateActionsRequest, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    detail = session_detail(client, row)
    actions = {item.id: item for item in detail.detected_actions}
    selected = [actions[action_id] for action_id in payload.action_ids if action_id in actions]
    if not selected:
        raise HTTPException(status_code=400, detail="Select at least one available action")
    results = await action_executor.execute_actions(selected, transcript=detail.transcript)
    for result in results:
        append_record(client, session_id, user.id, "result", result.model_dump(mode="json"))
        action = actions[result.action_id]
        action.status = ActionStatus.generated if result.status == "success" else ActionStatus.error
        append_record(client, session_id, user.id, "action", action.model_dump(mode="json"))
    client.table("haki_sessions").update({"status": SessionStatus.exported.value if any(r.status == "success" for r in results) else SessionStatus.ready.value}).eq("id", str(session_id)).execute()
    return results


@router.post("/{session_id}/ask", response_model=ActionResult)
async def ask_session(session_id: uuid.UUID, payload: AskRequest, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    detail = session_detail(client, row)
    instruction = payload.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="An instruction is required")
    action = DetectedAction(session_id=session_id, type=ActionType.llm_task, title=instruction[:70], preview=instruction, confidence=1.0, confidence_reason="Requested by you", extracted_fields={"instruction": instruction, **({"model": payload.model} if payload.model else {})}, pre_checked=True)
    append_record(client, session_id, user.id, "action", action.model_dump(mode="json"))
    result = await action_executor.execute_action(action, transcript=detail.transcript)
    action.status = ActionStatus.generated if result.status == "success" else ActionStatus.error
    append_record(client, session_id, user.id, "action", action.model_dump(mode="json"))
    append_record(client, session_id, user.id, "result", result.model_dump(mode="json"))
    return result
