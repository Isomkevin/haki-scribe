"""
Cross-cutting enrichment applied after detection, before storing the
action tray. Currently: Exa company lookups on workspace_matter/crm_entry
actions that name a client/contact. Kept separate from action_detector.py
because it's optional polish, not core detection logic — safe to extend
with more enrichment sources later without touching the detection prompt.
"""

from app.integrations import exa_client
from app.models.schemas import ActionType, DetectedAction


async def enrich_with_exa(actions: list[DetectedAction]) -> list[DetectedAction]:
    for action in actions:
        name = None
        if action.type == ActionType.workspace_matter:
            name = action.extracted_fields.get("client")
        elif action.type == ActionType.crm_entry:
            name = action.extracted_fields.get("contact_name")
        if not name:
            continue

        try:
            result = await exa_client.search_company(name)
        except Exception:  # noqa: BLE001 — enrichment is best-effort, never blocks the tray
            result = None

        if result:
            action.extracted_fields["background_info"] = result
    return actions
