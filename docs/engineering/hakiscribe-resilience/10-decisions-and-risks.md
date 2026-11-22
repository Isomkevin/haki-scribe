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

## ADR-012: hearings persistence — option (a) implemented 2026-11-23, (b) open

**Problem:** Hearings, candidates and confirmations are in-memory (`hearings.py`) while sessions persist (`store.json` / `DATABASE_URL`) and recordings persist on disk. A restart loses hearings and orphans their sessions and recordings. The hearings router and Zoom webhook are also mounted only when production auth is off.

**Proposed correction (not implemented):** (a) short term — include hearings in `storage._snapshot/_restore` like matters; (b) production — a repository over migration 003 tables with org scoping, and production-mode routers. Option (a) is low-risk; (b) needs a tenancy design pass.

**Status:** (a) implemented in Stage D. `hearings.snapshot/restore` ride on the storage snapshot, so they reach Postgres when `DATABASE_URL` is set, and every mutation saves. `storage` parks the raw payload because it loads before `hearings` finishes importing. Jobs left `queued`/`running` by a restart are restored as `error` so they can be re-run. Real backend restart verified (09). (b) remains open: in production-auth mode the hearings router and Zoom webhook are not mounted. The same is true of matters, contacts and integrations, so production hearings need the production-matters design first.

## Stage B risks

| Risk | Mitigation / status |
| --- | --- |
| Zoom `download_token` sent as `Authorization: Bearer` | Matches current Zoom docs as understood; not verified against a live tenant. If Zoom rejects, switch to `?access_token=` query param in `download_preferred`. |
| Graph `/me/onlineMeetings` is organiser-only; transcript/recording scopes need admin consent | Errors say so explicitly; documented in `.env.example` and adapter capability notes. |
| `/process` background tasks are in-process | Lost on restart; since Stage D they are restored as `error: interrupted by a server restart` and can be re-run. A job queue is still needed for production. |
| large-v3 on CPU is slow (realtime factor often > 1) | `.env.example` recommends small/medium for CPU-only boxes. |
| "Thinking" LLMs (e.g. gemma4) may wrap JSON in prose | `_parse_json_object` extracts the outermost `{…}`; qwen2.5:3b returned parseable JSON in every real proceedings run; detection uses Ollama JSON mode. gemma4 not run (RAM). |
| No-egress proof is at the httpx layer only | Firewalled container run still owed (09). |

## ADR-013: Whisper language safeguards from real measurements

**Context:** Stage B added a built-in EN/SW court-vocabulary `initial_prompt` for every request. In Stage D, real runs on Kiswahili (FLEURS sw_ke) showed: WER 0.77 with the prompt vs 0.66 without; one clip's whole "transcript" was the prompt text; auto-detect labelled a Kiswahili clip as Javanese.

**Decision:** (1) Apply the built-in prompt only when the caller explicitly sets a language listed in `WHISPER_LEGAL_PROMPT_LANGS` (default `en`), never for a guessed language. (2) Drop any segment repeating ≥5 consecutive prompt words, and count drops in `prompt_echo_dropped`. (3) Restrict auto-detection to `WHISPER_ALLOWED_LANGUAGES` (default `en,sw`) by re-running with the most probable allowed language, reported as `language_forced_from`.

**Why:** Text the speaker never said in a court record is worse than a missed word. Explicit language selection measurably beats auto-detection, so the Tracker now offers an EN/SW selector.

**Risk:** A speaker who really says ≥5 consecutive words of the English prompt would have that segment dropped. The prompt is a list of terms, so this is unlikely, but the drop count is reported so it isn't silent.

## ADR-014: Ollama on CPU — timeout and JSON mode

**Decision:** The Ollama request timeout comes from `OLLAMA_TIMEOUT_S` (default 600 s, was a hard-coded 120 s). Action detection uses Ollama's `response_format: json_object` and asks for `{"actions": [...]}`, which the existing parser already accepts.

**Why:** On the reference CPU host, qwen2.5:3b needed 140–185 s for proceedings extraction. Malformed JSON from the 3B model crashed demo-library detection.

## Stage D risks

| Risk | Mitigation / status |
| --- | --- |
| Kiswahili accuracy with `small` (WER ≈ 0.66 on read speech) | Documented as not fit for a legal record; use `large-v3` (GPU or patient CPU) or Intron Sahara in hybrid; court-audio WER still unmeasured |
| 3B local models are inconsistent at extraction | Rules pass + strict quote grounding + placeholder rejection; human `/review` required before filing |
| Host Ollama repaired by restoring only the CPU runner files | The next Ollama auto-update reinstalls everything (~5 GB incl. GPU libraries) and will fail the same way unless ≥6 GB is free |
| Docker image not rebuilt with the new server/requirements | Native venv verified; rebuild when Docker is available |
