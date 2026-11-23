# Handoff: HakiChain alignment Phase 1 (Cursor → Claude Code)

**Date:** 2026-11-23  
**Contract:** `2026-11` — see [12-hakichain-integration-contracts.md](../12-hakichain-integration-contracts.md)  
**Decisions:** Identity 1B (dual login + `hkc_`); delivery 2A (vertical slice first)

## Already done in this pass (Cursor)

### HakiScribe

- Contracts + fixtures under `docs/engineering/hakiscribe-resilience/`
- `hakichain_client.py`: `list_matters`, `get_matter`, `link_matter`, `upsert_hearing`, `finalize_transcript`
- Matter FKs: `hakichain_client_id`, `hakichain_workspace_id`, `hakichain_linked_at` (+ migration `005_hakichain_matter_link.sql`)
- `GET /integrations/hakichain/matters`, `GET …/matters/{workspace_id}`, `POST /integrations/hakichain/link-matter`
- `hearing_filing.py` prefers link → upsert → finalize; falls back to legacy `file_*` if new actions unavailable
- Tracker: Load/Link HakiChain WorkSpace picker; File to HakiChain unchanged entry point
- Tests: `test_hearing_filing.py`, `test_hakichain_pull.py`
- Checklist: `verification/hakichain-alignment-checklist.md`

### hakichain-demo-suite (implemented here; verify/deploy on your side)

- Migration: `supabase/migrations/20261123100000_hakiscribe_hearings.sql`
- Ingress expanded: `list_matters`, `get_matter`, `link_matter`, `upsert_hearing`, `finalize_transcript`; court-date → `courtScheduleEvents`; ACL via owner + `workspace_members`
- UI: `src/components/HakiScribeHearingsPanel.tsx` + Workspace **Hearings** tab

## Claude Code follow-ups

1. **Deploy** both migrations + edge function; set `HAKISCRIBE_WEBHOOK_SIGNING_SECRET` (and Scribe `HAKICHAIN_WEBHOOK_SECRET`).
2. Harden ingress Deno tests for ACL 403, firm-scope list_matters, content-update, webhook delivery.
3. Polish Hearings / Portal summary UI to design tokens if needed.
4. Confirm `workspace_members` column names; adjust ingress if live schema differs.
5. Live `hkc_` + webhook + portal proof; tick checklist evidence.

## Phase 2–3 landed (Cursor)

- Content-update `file_*`; webhooks register/dispatch; Scribe `/webhooks/hakichain` + reconcile
- Deep links preserved through `/haki-*` → tool-suite redirects; Draft/Review/Lens hydrate from `?hearing=`
- HakiDocs virtual **Hearings** folder (`hakiscribe-hearings`); Client Portal summaries
- Firm-scoped token ACL in ingress + Settings mint/webhook UI; Tracker `?hearing=` focus

## Action schemas (quick)

```text
list_matters   → { matters: [{ workspace_id, client_id, name, client, role }] }
get_matter     ← workspace_id | client_id → matter + hearings + docs + reminders
link_matter    ← action_key, workspace_id, scribe_matter_id → { client_id, workspace_id, workspace_url }
upsert_hearing ← scribe_hearing_id, workspace_id, title, status, …
finalize_transcript ← action_key, scribe_hearing_id, workspace_id, segments[], proceedings
```

## UI acceptance (HakiChain)

- Workspace tab **Hearings** lists `hakiscribe_hearings` for `matterWsUuid`
- Selecting a hearing shows segments + grounded/ungrounded proceedings disclaimer
- Activity: “Hearing transcript filed from HakiScribe” after finalize
- Do **not** build a second Tracker inside HakiChain

## Non-goals still deferred

SSO, `hakichain_v2`, realtime segment streaming, deep Draft/Lens/Review/Portal, firm-wide tokens.
