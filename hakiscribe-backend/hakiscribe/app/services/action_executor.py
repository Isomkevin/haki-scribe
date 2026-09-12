"""
Executes a DetectedAction once the user has selected it in the action
tray. Each type has its own generator function; `execute_action`
dispatches.

Where it lands: draft_document, calendar_event, and workspace_matter now
write into a real Ambiguous AI workspace (Docs, Calendar, CRM deals) when
AMBIGUOUS_API_KEY is set — falling back to local-only generation
otherwise, so the pipeline works identically with or without a
configured workspace. private_note and time_entry stay local by design
(private notes shouldn't leave the app; there's no time-tracking
primitive in Ambiguous's app set). crm_entry attempts a best-effort
Ambiguous CRM contact call. After a draft_document lands, a Chat
notification tells a human it's ready for review — this deliberately
never auto-sends anything substantive (e.g. via Mail) without a person
in the loop.
"""

import os
import uuid
from datetime import datetime, timedelta

import httpx

from app.integrations import ambiguous_client
from app.models.schemas import ActionResult, ActionType, DetectedAction, Matter
from app.services import storage

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Routed through OpenRouter but pointed at an OpenAI model by default —
# genuinely exercises both sponsors rather than picking one arbitrarily.
DRAFTING_MODEL = os.environ.get("DRAFTING_MODEL", "openai/gpt-4o")

DRAFTING_SYSTEM_PROMPT = """You are a legal drafting assistant. Given \
the document kind and facts extracted from a transcript, draft the \
document in professional legal register. Use placeholders like \
"[DATE]" or "[ADDRESS]" for anything not supplied. Output only the \
document text, no commentary."""


async def _generate_draft_document(action: DetectedAction) -> dict:
    fields = action.extracted_fields
    prompt = (
        f"Document kind: {fields.get('document_kind', 'legal memo')}\n"
        f"Parties: {fields.get('parties', 'not specified')}\n"
        f"Key facts: {fields.get('key_facts', '')}"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            json={
                "model": DRAFTING_MODEL,
                "messages": [
                    {"role": "system", "content": DRAFTING_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        document_text = response.json()["choices"][0]["message"]["content"]

    result = {"document_text": document_text, "document_kind": fields.get("document_kind")}

    doc = await ambiguous_client.create_document(title=action.title, body_text=document_text)
    if doc:
        result["ambiguous_document_id"] = doc.get("id")
        # Tell a human it's ready — never auto-send the substantive
        # content itself (e.g. via Mail) without review.
        await ambiguous_client.post_chat_message(
            f"Draft ready for review: **{action.title}** — {action.preview}"
        )
    return result


async def _generate_calendar_event(action: DetectedAction) -> dict:
    fields = action.extracted_fields
    title = fields.get("title", action.title)
    # Best-effort parse; fall back to "one week from now" so the demo
    # never breaks on an ambiguous date extracted from speech.
    try:
        start = datetime.fromisoformat(f"{fields.get('date')}T{fields.get('time', '09:00')}")
    except (ValueError, TypeError):
        start = datetime.utcnow() + timedelta(days=7)
    end = start + timedelta(hours=1)

    ics = "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{title}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    result = {"title": title, "start": start.isoformat(), "ics": ics}

    event = await ambiguous_client.create_calendar_event(title, start.isoformat(), end.isoformat())
    if event:
        result["ambiguous_event_id"] = event.get("id")
    return result


def _generate_private_note(action: DetectedAction) -> dict:
    return {"note_text": action.extracted_fields.get("note_text", action.preview)}


def _generate_time_entry(action: DetectedAction) -> dict:
    fields = action.extracted_fields
    return {
        "duration_hours": fields.get("duration_hours"),
        "activity_description": fields.get("activity_description", action.preview),
        "matter_name": fields.get("matter_name"),
        "billable": True,
    }


async def _generate_workspace_matter(action: DetectedAction) -> dict:
    fields = action.extracted_fields
    existing_id = fields.get("existing_matter_id")
    if existing_id:
        local_matter = next((m for m in storage.list_matters() if str(m.id) == str(existing_id)), None)
        if local_matter and local_matter.ambiguous_deal_id:
            await ambiguous_client.update_deal(local_matter.ambiguous_deal_id, name=fields.get("matter_name"))
        return {
            "matter_id": existing_id,
            "matter_name": fields.get("matter_name", action.title),
            "note": "linked to existing matter",
        }

    # No match — create a real Matter record so the *next* session with
    # this client is recognized as a continuation, not a fresh new matter.
    matter = Matter(
        client_name=fields.get("client", fields.get("matter_name", action.title)),
        matter_name=fields.get("matter_name", action.title),
    )

    deal = await ambiguous_client.create_deal(matter.matter_name, matter.client_name)
    if deal:
        matter.ambiguous_deal_id = deal.get("id")
    storage.create_matter(matter)

    return {
        "matter_id": str(matter.id),
        "matter_name": matter.matter_name,
        "ambiguous_deal_id": matter.ambiguous_deal_id,
        "note": "new matter created" + (" in Ambiguous CRM" if deal else " (Ambiguous not configured)"),
    }


async def _generate_crm_entry(action: DetectedAction) -> dict:
    fields = action.extracted_fields
    contact = await ambiguous_client.create_contact(fields.get("contact_name", ""), fields.get("updates", {}))
    if contact:
        return {
            "contact_id": contact.get("id"),
            "contact_name": fields.get("contact_name"),
            "note": "created in Ambiguous CRM",
        }
    return {
        "contact_id": f"stub-{uuid.uuid4().hex[:8]}",
        "contact_name": fields.get("contact_name"),
        "note": "Ambiguous not configured — local stub only",
    }


async def execute_action(action: DetectedAction) -> ActionResult:
    try:
        if action.type == ActionType.draft_document:
            result = await _generate_draft_document(action)
        elif action.type == ActionType.calendar_event:
            result = await _generate_calendar_event(action)
        elif action.type == ActionType.private_note:
            result = _generate_private_note(action)
        elif action.type == ActionType.time_entry:
            result = _generate_time_entry(action)
        elif action.type == ActionType.workspace_matter:
            result = await _generate_workspace_matter(action)
        elif action.type == ActionType.crm_entry:
            result = await _generate_crm_entry(action)
        else:
            raise ValueError(f"Unknown action type: {action.type}")
        return ActionResult(action_id=action.id, type=action.type, status="success", result=result)
    except Exception as exc:  # noqa: BLE001 — surface any failure per-action, not as a 500
        return ActionResult(action_id=action.id, type=action.type, status="error", result={}, error=str(exc))
