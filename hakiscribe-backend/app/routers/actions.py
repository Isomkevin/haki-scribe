import uuid

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ActionResult,
    ActionStatus,
    ActionType,
    AskRequest,
    DetectedAction,
    GenerateActionsRequest,
)
from app.services import action_detector, action_executor, enrichment, storage, trigger_client

router = APIRouter()


@router.post("/{session_id}/detect", response_model=list[DetectedAction])
async def detect_actions(session_id: uuid.UUID):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not detail.transcript:
        raise HTTPException(status_code=400, detail="Session has no transcript yet")

    known_matters = storage.list_matters()

    # Prefer running detection as a Trigger.dev background task (durable,
    # retried, observable). If Trigger.dev isn't configured, fall back to
    # calling the same logic directly in-process — identical result either way.
    trigger_output = await trigger_client.trigger_and_wait(
        "detect-actions",
        {
            "session_id": str(session_id),
            "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
            "flags": [f.model_dump(mode="json") for f in detail.flagged_moments],
            "known_matters": [m.model_dump(mode="json") for m in known_matters],
            "session_title": detail.title,
        },
    )
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
    return actions


@router.get("/{session_id}/actions", response_model=list[DetectedAction])
def list_actions(session_id: uuid.UUID):
    if storage.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return storage.get_detected_actions(session_id)


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
        # Same durable-task-with-fallback pattern as detection.
        trigger_output = await trigger_client.trigger_and_wait(
            "generate-actions",
            {
                "actions": [a.model_dump(mode="json") for a in to_run],
                "transcript": [seg.model_dump(mode="json") for seg in detail.transcript],
            },
        )
        if trigger_output is not None:
            run_results = [ActionResult(**r) for r in trigger_output]
        else:
            run_results = [await action_executor.execute_action(a, transcript=detail.transcript) for a in to_run]

        for result in run_results:
            storage.update_action_status(
                session_id, result.action_id, ActionStatus.generated if result.status == "success" else ActionStatus.error
            )
        results.extend(run_results)
        storage.upsert_action_results(session_id, results)

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
