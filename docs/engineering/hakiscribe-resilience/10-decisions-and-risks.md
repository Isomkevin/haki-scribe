# 10 — Decisions and risks (ADRs)

## ADR-001: Frontier models remain first-class

**Decision:** Default `HAKISCRIBE_AI_MODE=cloud`. Local providers are additive. Never remove Anthropic, OpenAI, Gemini, Groq, Mistral, OpenRouter, Nebius, `claude_custom`, or NIM paths.

**Why:** Product quality and existing deployments depend on frontier models when connected.

## ADR-002: Hybrid is explicit per-task routing

**Decision:** Mode `hybrid` uses `HAKISCRIBE_ROUTE_*` (and Settings UI). No silent cloud↔local swap. Optional fallback only when `HAKISCRIBE_HYBRID_FALLBACK=explicit_allow` and logged in `ai_runs`.

**Why:** Firms need local ASR for privacy with Claude/ChatGPT for drafting without air-gapping the whole desk.

## ADR-003: Four modes, not a boolean

**Decision:** `cloud` | `hybrid` | `private` | `local_only`.

- `private` = self-hosted/VPC endpoints (NIM, Ollama, custom URL), no public SaaS AI
- `local_only` = Compose local only, fail closed

## ADR-004: Virtual court starts with ingest + matter resolution

**Decision:** Stage A ships Calendar import, manual upload, Teams/Zoom OAuth+list contracts, and confidence-based matter matching with human confirm. Live bots deferred to Stage B where official APIs allow.

## ADR-005: Compose under `deploy/local-inference/`

**Decision:** Keep root clean for Lovable dual-deploy; no platform-specific `vercel.json` unless required.

## Risks

| Risk | Mitigation |
| --- | --- |
| Over-broad cloud block breaks frontier in cloud/hybrid | Mode- and route-scoped gates + regression tests |
| NIM ASR silent Whisper fallback in local_only | Disable cross-realm fallback when mode forbids cloud |
| Trigger.dev cloud worker in local_only | Prefer in-process when `local_only` |
| Zoom/Teams admin policy blocks recordings | Document; never fabricate join |
| Hybrid misconfig | Validate routes against connected creds + health before save |

## Stage B decisions (Claude Code)

## ADR-006: Platform transcripts are first-class input

**Decision:** Teams/Zoom WebVTT transcripts are ingested directly (`/transcript`, `fetch-recording?prefer=transcript`) and bypass ASR. Teams fetch prefers transcript; Zoom prefers audio.

**Why:** Platform transcripts carry real participant names — better speaker attribution than acoustic diarization, at zero compute. Zoom defaults to audio because its transcription quality for Kiswahili is unproven; our ASR applies the EN/SW legal prompt.

## ADR-007: Proceedings findings must be quote-grounded

**Decision:** Every LLM item needs a verbatim quote that resolves (after case/punctuation normalisation) to one segment or an adjacent pair of non-privileged segments. Otherwise it goes to `ungrounded`. Deterministic rules run alongside and are labelled `method: rules`.

**Why:** A wrong next-court-date is a malpractice risk. Exact matching rejects some paraphrased-but-true items; that is the intended trade-off.

## ADR-008: Recordings are local-first

**Decision:** `recording_store` always writes to `HAKISCRIBE_RECORDINGS_DIR`; S3 is a mirror. Keys are server-built from hearing id + sanitised filename.

**Why:** `local_only` must not need S3; Stage A silently dropped bytes.

## ADR-009: Hearing lifecycle is an explicit state machine; matter link locks at capture

**Decision:** `hearings.ALLOWED_TRANSITIONS`. Re-match/re-import only moves `scheduled|pending_confirm`. Confirm/reject only before a session exists. Processing requires a confirmed matter; a recording arriving first waits.

**Why:** Fixes re-import wiping human confirmations; keeps "never silently attach".

## ADR-010: No live bots in Stage B

**Decision:** Not built. Recording/transcript retrieval after the hearing only.

**Why:** Teams requires an Azure Bot / calling-bot registration and policy-based recording; Zoom requires the Meeting SDK bot model and host consent. Neither was in scope or authorised.

## ADR-011: Health is shallow by default, deep on request

**Decision:** `/health` stays fast; `/integrations/ai-mode?deep=true` runs a 1-token Ollama generation.

**Why:** Found in practice — a listed model can be unloadable.

## ADR-012 (open — needs decision): hearings persistence

**Problem:** Hearings, candidates and confirmations are in-memory (`hearings.py`) while sessions persist (`store.json` / `DATABASE_URL`) and recordings persist on disk. A restart loses hearings and orphans their sessions and recordings. The hearings router and Zoom webhook are also mounted only when production auth is off.

**Proposed correction (not implemented):** (a) short term — include hearings in `storage._snapshot/_restore` like matters; (b) production — a repository over migration 003 tables with org scoping, and production-mode routers. Option (a) is low-risk; (b) needs a tenancy design pass. Left for Cursor/owner to choose.

## Stage B risks

| Risk | Mitigation / status |
| --- | --- |
| Zoom `download_token` sent as `Authorization: Bearer` | Matches current Zoom docs as understood; not verified against a live tenant. If Zoom rejects, switch to `?access_token=` query param in `download_preferred`. |
| Graph `/me/onlineMeetings` is organiser-only; transcript/recording scopes need admin consent | Errors say so explicitly; documented in `.env.example` and adapter capability notes. |
| `/process` background tasks are in-process | Lost on restart; state stays `queued`/`running`. Re-POST to retry. Needs a job queue for production. |
| large-v3 on CPU is slow (realtime factor often > 1) | `.env.example` recommends small/medium for CPU-only boxes. |
| "Thinking" LLMs (e.g. gemma4) may wrap JSON in prose | `_parse_json_object` extracts the outermost `{…}`; unverified on a real model. |
| No-egress proof is at the httpx layer only | Firewalled container run still owed (09). |
