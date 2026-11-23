# 12 — HakiChain ↔ HakiScribe integration contracts

**Contract version:** `2026-11`  
**Identity model:** 1B — dual login; bridge is lawyer `hkc_` token + `hakiscribe-ingress`.  
**HakiChain repo of record:** `hakichain-demo-suite`  
**Endpoint:** `POST {HAKICHAIN_API_BASE}` (Supabase edge `hakiscribe-ingress`)  
**Headers (scribe):** `Authorization: Bearer hkc_…`, `apikey: <anon>`, `Content-Type: application/json`

New actions SHOULD include `"contract_version": "2026-11"` in the body. Legacy `me` / `file_*` remain without it.

## Canonical identifiers

| Entity | Authority | Identifier |
| --- | --- | --- |
| Matter / Workspace | HakiChain | `workspaces.id` (uuid) + public `client_id` (URL `?ws=`) |
| Lawyer | HakiChain | `profiles.id` via `hakiscribe_tokens.user_id` |
| HakiScribe user / org | HakiScribe | Local only; mapped through linked `hkc_` |
| Hearing | Dual | HakiScribe `hearing.id` ↔ HakiChain `hakiscribe_hearings.scribe_hearing_id` |
| Transcript / proceedings | HakiScribe until finalize | Then `hakiscribe_hearing_segments` + `proceedings` jsonb + optional `haki_docs` |

## Ownership rules

1. HakiChain `workspaces` are canonical matters. Prefer `link_matter` to an existing workspace over inventing `hs-{scribeUuid}` duplicates.
2. HakiScribe may keep a local matter row with FKs: `hakichain_client_id`, `hakichain_workspace_id`, `hakichain_linked_at`.
3. Live transcription state lives in HakiScribe until `finalize_transcript`.
4. ACL: every `hkc_` read/write must verify the token owner is workspace owner or `workspace_members` member. Service role stays inside the edge function only.

## Ingress actions (Phase 1)

### Existing (unchanged semantics)

| Action | Auth | Notes |
| --- | --- | --- |
| `create_token` / `list_tokens` / `revoke_token` | Lawyer JWT | Mint/manage `hkc_` |
| `me` | `hkc_` | `{ ok, user_id, account, email }` |
| `file_matter` | `hkc_` | Creates/updates workspace by `hs-…` client_id (legacy path) |
| `file_document` | `hkc_` | Text blob into `haki_docs` + snapshot; prefer `doc_type` hearing-aware |
| `file_reminder` | `hkc_` | Reminder row + snapshot; court-date should also patch `courtScheduleEvents` |

### New (contract `2026-11`)

#### `list_matters`

```json
{ "action": "list_matters", "contract_version": "2026-11" }
```

Response:

```json
{
  "ok": true,
  "matters": [
    {
      "workspace_id": "uuid",
      "client_id": "string",
      "name": "string",
      "client": "string",
      "matter_details": {},
      "role": "owner|member"
    }
  ]
}
```

#### `get_matter`

```json
{
  "action": "get_matter",
  "contract_version": "2026-11",
  "workspace_id": "uuid",
  "client_id": "optional-if-no-workspace_id"
}
```

Response includes metadata, members/team, recent documents summary, reminders, prior `hakiscribe_hearings`.

#### `link_matter`

Bind scribe local matter/hearing to an **existing** HakiChain workspace (no invent):

```json
{
  "action": "link_matter",
  "contract_version": "2026-11",
  "action_key": "link:{scribe_matter_id}",
  "workspace_id": "uuid",
  "scribe_matter_id": "uuid-string"
}
```

Response: `{ ok, client_id, workspace_id, workspace_url, reused }`.

#### `upsert_hearing`

```json
{
  "action": "upsert_hearing",
  "contract_version": "2026-11",
  "scribe_hearing_id": "uuid",
  "workspace_id": "uuid",
  "title": "string",
  "status": "scheduled|capturing|transcribed|reviewed|filed",
  "case_reference": "optional",
  "starts_at": "ISO-8601 optional",
  "meeting_url": "optional",
  "metadata": {}
}
```

Idempotent on `(owner_user_id, scribe_hearing_id)`.

#### `finalize_transcript`

```json
{
  "action": "finalize_transcript",
  "contract_version": "2026-11",
  "action_key": "hearing-finalize:{scribe_hearing_id}",
  "scribe_hearing_id": "uuid",
  "workspace_id": "uuid",
  "segments": [
    { "start_ms": 0, "end_ms": 1000, "speaker": "Court", "text": "…", "redacted": false }
  ],
  "proceedings": {},
  "title": "optional override"
}
```

Replaces segments; updates proceedings; upserts/updates `haki_docs` content (not freeze-only); writes activity.

## Shared fixture shapes

See [`fixtures/hakichain-ingress-2026-11.json`](./fixtures/hakichain-ingress-2026-11.json) for request/response examples used by mocked tests.

## Phase 1 lifecycle (sync, no webhook bus)

1. Link `hkc_` in HakiScribe Connectors → `me`
2. `list_matters` → pick → `link_matter` + store FKs on local matter
3. Hearing confirm → `upsert_hearing` (scheduled)
4. Process / review locally
5. File → `finalize_transcript` + `file_reminder` for next dates
6. Advocate opens HakiChain Workspace → Hearings panel

## Explicit non-goals (Phase 1)

SSO replacement, `hakichain_v2`, realtime segment streaming, deep HakiDraft/Lens/Review/Portal, firm-wide tokens.
