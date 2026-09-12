"""
Executes a DetectedAction once the user has selected it in the action
tray. Each type has its own generator function; `execute_action`
dispatches.

draft_document, calendar_event, and time_entry are produced by the
transcript-grounded models in generation.py. workspace_matter and
crm_entry persist through the same workspace helpers as POST /matters
and POST /contacts so Session Library stays in sync. Ambiguous AI is
used when configured; otherwise results stay local.
"""

from __future__ import annotations

from uuid import UUID

from app.integrations import ambiguous_client, exa_client, llm_client
from app.models.schemas import (
    ActionResult,
    ActionType,
    DetectedAction,
    LlmTaskResult,
    ResearchResult,
    ResearchSource,
    TranscriptSegment,
)
from app.services import generation, storage, workspace

RESEARCH_SYSTEM_PROMPT = (
    "You are a Kenyan advocate's research assistant. Answer the question using ONLY "
    "the retrieved sources supplied below. Cite the source number inline like [1]. "
    "State the governing statute or authority where the sources give one. If the "
    "sources do not answer the question, say so plainly instead of guessing. Never "
    "invent a case, section, citation or date. Keep it under 300 words."
)

ASK_SYSTEM_PROMPT = (
    "You are assisting a Kenyan legal professional. Answer the instruction using ONLY "
    "the verified, non-redacted transcript supplied. Never invent parties, figures, "
    "dates or authorities; mark anything not on the record as [NOT ON THE RECORD]. "
    "Be concise and practical."
)


async def _generate_draft_document(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    drafted = await generation.draft_document_model.generate(action, transcript)
    result = drafted.model_dump()

    doc = await ambiguous_client.create_document(title=action.title, body_text=drafted.document_text)
    if doc:
        result["ambiguous_document_id"] = doc.get("id")
        await ambiguous_client.post_chat_message(
            f"Draft ready for review: **{action.title}** — {action.preview}"
        )
    return result


async def _generate_calendar_event(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    event = await generation.calendar_event_model.generate(action, transcript)
    result = event.model_dump()

    remote = await ambiguous_client.create_calendar_event(event.title, event.start, event.end)
    if remote:
        result["ambiguous_event_id"] = remote.get("id")
    return result


def _generate_private_note(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    note = action.extracted_fields.get("note_text") or action.preview
    record = generation.format_transcript(transcript)
    if record and note and note not in record:
        note = f"{note}\n\nSource:\n{record}"
    return {"note_text": note}


async def _generate_time_entry(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    entry = await generation.time_entry_model.generate(action, transcript)
    return entry.model_dump()


async def _generate_workspace_matter(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    fields = action.extracted_fields
    speakers = generation.speakers_from_transcript(transcript)
    client_name = str(fields.get("client") or (speakers[0] if speakers else "") or action.title)
    matter_name = str(fields.get("matter_name") or action.title)
    existing_id = fields.get("existing_matter_id")

    deal = None
    local_existing = None
    if existing_id:
        try:
            local_existing = storage.get_matter(UUID(str(existing_id)))
        except ValueError:
            local_existing = next((item for item in storage.list_matters() if str(item.id) == str(existing_id)), None)
        if local_existing and local_existing.ambiguous_deal_id:
            deal = await ambiguous_client.update_deal(local_existing.ambiguous_deal_id, name=matter_name)

    if deal is None and not existing_id:
        deal = await ambiguous_client.create_deal(matter_name, client_name)

    matter, outcome = workspace.persist_matter(
        client_name=client_name,
        matter_name=matter_name,
        session_id=action.session_id,
        existing_matter_id=str(existing_id) if existing_id else None,
        ambiguous_deal_id=(deal or {}).get("id") if deal else None,
    )
    contact = workspace.persist_contact(
        name=client_name,
        updates={"role": "client", "source": "workspace_matter"},
        session_id=action.session_id,
        matter_id=matter.id,
    )

    return {
        "matter_id": str(matter.id),
        "matter_name": matter.matter_name,
        "client_name": matter.client_name,
        "contact_id": str(contact.id),
        "contact_name": contact.name,
        "ambiguous_deal_id": matter.ambiguous_deal_id,
        "note": (
            f"{'linked to existing' if outcome == 'linked' else 'new'} matter persisted via /matters"
            + (" and mirrored to Ambiguous CRM" if deal else "")
        ),
    }


async def _generate_crm_entry(action: DetectedAction, transcript: list[TranscriptSegment]) -> dict:
    fields = action.extracted_fields
    speakers = generation.speakers_from_transcript(transcript)
    contact_name = str(fields.get("contact_name") or (speakers[0] if speakers else "") or "Unnamed contact")
    updates = fields.get("updates") if isinstance(fields.get("updates"), dict) else {"note": fields.get("updates")}
    if not updates:
        updates = {"source": "crm_entry", "preview": action.preview}

    remote = await ambiguous_client.create_contact(contact_name, updates)
    session_matters = storage.get_session(action.session_id)
    matter_id = session_matters.matters[0].id if session_matters and session_matters.matters else None
    contact = workspace.persist_contact(
        name=contact_name,
        updates=updates,
        session_id=action.session_id,
        matter_id=matter_id,
        ambiguous_contact_id=(remote or {}).get("id") if remote else None,
    )
    return {
        "contact_id": str(contact.id),
        "contact_name": contact.name,
        "matter_id": str(matter_id) if matter_id else None,
        "note": "created in Ambiguous CRM" if remote else "persisted in Session Library",
        "updates": contact.updates,
    }


async def execute_action(
    action: DetectedAction,
    transcript: list[TranscriptSegment] | None = None,
) -> ActionResult:
    record = transcript if transcript is not None else storage.get_transcript(action.session_id)
    try:
        if action.type == ActionType.draft_document:
            result = await _generate_draft_document(action, record)
        elif action.type == ActionType.calendar_event:
            result = await _generate_calendar_event(action, record)
        elif action.type == ActionType.private_note:
            result = _generate_private_note(action, record)
        elif action.type == ActionType.time_entry:
            result = await _generate_time_entry(action, record)
        elif action.type == ActionType.workspace_matter:
            result = await _generate_workspace_matter(action, record)
        elif action.type == ActionType.crm_entry:
            result = await _generate_crm_entry(action, record)
        else:
            raise ValueError(f"Unknown action type: {action.type}")
        return ActionResult(action_id=action.id, type=action.type, status="success", result=result)
    except Exception as exc:  # noqa: BLE001 — surface any failure per-action, not as a 500
        return ActionResult(action_id=action.id, type=action.type, status="error", result={}, error=str(exc))
