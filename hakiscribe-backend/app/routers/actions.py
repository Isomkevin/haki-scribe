import uuid

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    ActionResult,
    ActionStatus,
    ActionType,
    AskRequest,
    DetectedAction,
    GenerateActionsRequest,
    SessionStatus,
)
from app.services import action_detector, action_executor, enrichment, storage, trigger_client

router = APIRouter()


@router.post("/{session_id}/detect", response_model=list[DetectedAction])
async def detect_actions(session_id: uuid.UUID, force: bool = Query(default=False)):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not detail.transcript:
        raise HTTPException(status_code=400, detail="Session has no transcript yet")
    if detail.detected_actions and not force:
        return detail.detected_actions

    storage.update_session_status(session_id, SessionStatus.processing)
    known_matters = storage.list_matters()
    payload = {
        "session_id": str(session_id),
        "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
        "flags": [f.model_dump(mode="json") for f in detail.flagged_moments],
        "known_matters": [m.model_dump(mode="json") for m in known_matters],
        "session_title": detail.title,
    }

    trigger_output = await trigger_client.trigger_and_wait("detect-actions", payload, timeout_s=180.0)
    if trigger_output is not None:
        actions = [DetectedAction(**a) for a in trigger_output]
    else:
        actions = await action_detector.detect_actions(
            session_id,
            detail.transcript,
            flags=detail.flagged_moments,
            known_matters=known_matters,
            session_title=detail.title,
        )

    actions = await enrichment.enrich_with_exa(actions)
    storage.set_detected_actions(session_id, actions)
    storage.update_session_status(session_id, SessionStatus.ready)
    return actions


@router.get("/{session_id}/actions", response_model=list[DetectedAction])
def list_actions(session_id: uuid.UUID):
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return storage.get_detected_actions(session_id)


@router.post("/{session_id}/actions/{action_id}/dismiss", response_model=DetectedAction)
def dismiss_action(session_id: uuid.UUID, action_id: uuid.UUID):
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    action = storage.update_action_status(session_id, action_id, ActionStatus.dismissed)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/{session_id}/generate", response_model=list[ActionResult])
async def generate_actions(session_id: uuid.UUID, payload: GenerateActionsRequest):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")

    to_run: list[DetectedAction] = []
    results: list[ActionResult] = []
    for action_id in payload.action_ids:
        action = storage.get_action(session_id, action_id)
        if action is None:
            results.append(
                ActionResult(action_id=action_id, type="draft_document", status="error", error="Action not found")
            )
            continue
        overrides = payload.field_overrides.get(str(action_id), {})
        if overrides:
            action = storage.update_action_fields(session_id, action_id, overrides) or action
        to_run.append(action)

    if to_run:
        trigger_output = await trigger_client.trigger_and_wait(
            "generate-actions",
            {
                "actions": [a.model_dump(mode="json") for a in to_run],
                "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
            },
            # Research + model passes are slower than drafting — wait longer
            # before falling back, instead of timing out mid-generation.
            timeout_s=240.0,
        )
        if trigger_output is not None:
            run_results = [ActionResult(**r) for r in trigger_output]
        else:
            run_results = await action_executor.execute_actions(to_run, transcript=detail.transcript)

        for result in run_results:
            storage.update_action_status(
                session_id, result.action_id, ActionStatus.generated if result.status == "success" else ActionStatus.error
            )
        results.extend(run_results)
        storage.upsert_action_results(session_id, results)
        if any(item.status == "success" for item in run_results):
            storage.update_session_status(session_id, SessionStatus.exported)

    return results


@router.post("/{session_id}/ask", response_model=ActionResult)
async def ask_session(session_id: uuid.UUID, payload: AskRequest):
    """Ad-hoc instruction run against the verified transcript on whichever
    model the user picked. Stored as a normal llm_task card so it lives in
    the tray and the results list alongside everything else."""
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    instruction = payload.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="An instruction is required")

    action = DetectedAction(
        session_id=session_id,
        type=ActionType.llm_task,
        title=instruction[:70],
        preview=instruction,
        confidence=1.0,
        confidence_reason="Requested by you",
        extracted_fields={"instruction": instruction, **({"model": payload.model} if payload.model else {})},
        pre_checked=True,
    )
    storage.set_detected_actions(session_id, [*storage.get_detected_actions(session_id), action])

    trigger_output = await trigger_client.trigger_and_wait(
        "generate-actions",
        {
            "actions": [action.model_dump(mode="json")],
            "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
        },
        timeout_s=180.0,
    )
    if trigger_output:
        result = ActionResult(**trigger_output[0])
    else:
        result = await action_executor.execute_action(action, transcript=detail.transcript)

    storage.update_action_status(
        session_id, result.action_id, ActionStatus.generated if result.status == "success" else ActionStatus.error
    )
    storage.upsert_action_results(session_id, [result])
    return result
