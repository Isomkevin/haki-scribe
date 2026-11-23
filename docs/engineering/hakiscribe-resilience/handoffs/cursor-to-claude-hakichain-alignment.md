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

1. **Deploy** migration + edge function to the live Supabase project used by HakiScribe `HAKICHAIN_API_BASE`.
2. Harden ingress tests (Deno) for ACL denial (403) and idempotent finalize content replace.
3. Polish Hearings tab empty/error states to match Haki design tokens if anything looks off.
4. Phase 2 stubs: webhook receiver design, HakiDocs “Hearings” folder, Reminder parity.
5. Confirm `workspace_members` column names match production (`user_id` / `workspace_id`) — adjust ingress if the live schema differs.
6. Live `hkc_` proof against checklist; update `08-implementation-status.md` E8/E9 with evidence.

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
