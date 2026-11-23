# 08 — Implementation status

Updated at end of Claude Code Stage B (2026-11-22). Stage A rows are unchanged from Cursor.

Legend: **Tested** = automated tests pass in this repo · **Contract-tested** = tested against stubbed/mocked external APIs, never against the real service · **Not run** = code exists but no real run · **Blocked** = verification blocked by an external dependency · **Not implemented**.

## Stage A (Cursor)

| Item | Status | Notes |
| --- | --- | --- |
| Engineering doc pack | done | `docs/engineering/hakiscribe-resilience/` |
| `ai_mode` + hybrid routes | done | `ai_mode.py`, `/integrations/ai-mode` |
| Local Whisper + Ollama | done | Additive providers; Compose CPU stack |
| Compose CPU/GPU | done | `deploy/local-inference/` |
| Hearings schema/API | done | migration 003 + in-memory demo store |
| Court adapters | done | Calendar import; Teams/Zoom list + OAuth stubs |
| Settings / hearing UI | done | Settings → AI mode; Tracker hearings panel |
| Unit tests | done | `test_ai_mode`, `test_matter_resolution` + regression 23 passed |
| cursor-to-claude handoff | done | `handoffs/cursor-to-claude.md` |

## Stage B (Claude Code)

| # | Item | Status | Evidence / gap |
| --- | --- | --- | --- |
| 1 | Local LLM (Ollama) for proceedings / detect | **Real-verified** (qwen2.5:3b, CPU) | Host Ollama repaired (CPU runner restored, 2026-11-23). Proceedings + action detection run for real in `local_only` with loopback-only egress. Quality of a 3B model is uneven (see 09); `OLLAMA_TIMEOUT_S` (default 600) and JSON mode added after real-run failures. |
| 2 | Ollama readiness | **Tested + real-verified** | `check_ollama(deep=True)` 1-token probe; against the broken host install it correctly reports `ok=false` where the shallow probe said `ok=true`. `model_available` flags un-pulled `OLLAMA_MODEL`. |
| 3 | faster-whisper server hardening (verbose_json, VAD params, legal prompt, `/ready`, threadpool, Windows-safe temp file) | **Real-verified** (`small`, CPU, native venv) | Real runs found and fixed: PyAV 19 incompatibility (pinned `av<15`), decode vs server errors (422/500), legal prompt echoed as transcript on Kiswahili (now English-only + echo guard), auto-detect choosing Javanese (now limited to `en,sw`). Docker image not rebuilt (Docker daemon off). |
| 4 | Diarization (pyannote, opt-in) | Code: done. Speaker assignment **tested**. **pyannote run: Not run** | Needs `WITH_DIARIZATION=1` build, `HF_TOKEN` with pyannote terms accepted, ~2 GB. Disabled path reports the reason instead of inventing speakers. |
| 5 | Platform speaker labels (Teams/Zoom WebVTT) | **Tested** | `vtt.py`; Teams `<v Name>` and Zoom `Name:` dialects. |
| 6 | EN/SW transcription | EN **real-verified**. Kiswahili **measured: not fit for a legal record with `small`** | EN synthetic hearing: accurate, timestamped. Kiswahili (6 FLEURS sw_ke clips, 122 words): WER 0.66 with `language=sw`, 0.69 auto. Needs `large-v3` (≥3 GB disk) or Intron Sahara (hybrid) — not court audio either way. |
| 7 | Proceedings intelligence with quote grounding | **Tested** (LLM mocked) | Rules (EN+SW, no AI) + LLM extraction; items without a verbatim transcript quote → `ungrounded`; privileged lines never reach the prompt; stale provenance bug avoided. |
| 8 | Hybrid fallback logging (`ai_runs`) | **Tested** | `cloud_fallback_allowed` / `record_fallback`; NIM→OpenRouter in ASR and generation. |
| 9 | Zoom: recording download + `recording.completed` webhook | **Contract-tested** | Signature + replay window + URL validation + download with `download_token`. **No real Zoom tenant used.** |
| 10 | Teams: transcript / recording via Graph | **Contract-tested** | JoinWebUrl → onlineMeeting → transcripts (VTT) → fallback recordings; actionable 403/404 errors. **No real tenant used.** OAuth scopes extended. |
| 11 | Live meeting bots | **Implemented (contract)** — ADR-015 | Official Teams calling-bot + Zoom Meeting SDK adapters; Tracker Start/Stop capture. Live sandbox **not run** (1B). |
| 12 | Recording persistence | **Tested** (local volume) · S3 mirror **Not run** | Fixes Stage A bug: `/upload` discarded bytes (`object_store.put_bytes` did not exist). Path-traversal-safe keys; size cap. |
| 13 | Matter Resolution Engine | **Tested** | Canonical Kenyan case refs (`E045 of 2024` = `E45/2024`), boundary-safe matching, conflicting-case-number penalty, near-tie ambiguity. |
| 14 | Hearing lifecycle | **Tested** | Explicit transition table; fixes Stage A bug where re-importing a calendar/Teams/Zoom event reset human confirmations; matter link locked after capture; idempotent session creation. |
| 15 | Post-hearing pipeline (`/process`) | **Tested + real-verified** | Background mode tested and run over real HTTP against real Whisper + Ollama (see Stage D). Refuses before human confirm; `transcribed` then human `/review`. |
| 16 | Frontend API client for new endpoints | Done, typechecked | `src/lib/hakiscribe.ts`. |
| 16b | Tracker UI wired to Stage B lifecycle | **Done**, typechecked, **not browser-tested** | Stage C wiring; Stage D fixes listed below. |

## Stage C connection pass (Cursor)

| Item | Status | Notes |
| --- | --- | --- |
| Backend Stage B verification | done | `pytest` → **88 passed, 2 skipped** |
| Frontend vitest | done | **22 passed** |
| Tracker ↔ hearings pipeline | done | Full match → ingest → process → review → File to HakiChain UI |
| AI mode Settings ↔ deep probe | done | `getAiMode(true)` → Ollama generation probe |
| ADR-012 hearings persistence | **(a)+(b) complete** | Demo snapshot + `/production/hearings` + org webhook |

## Stage D — real-stack completion (Claude Code, 2026-11-23)

Host unblocked: disk freed to 4.4 GB; Ollama's missing CPU runner (`lib/ollama`, ~41 MB) restored from the matching 0.40.16 release; `qwen2.5:3b` pulled; faster-whisper installed natively. Docker still off.

| # | Item | Status | Evidence / gap |
| --- | --- | --- | --- |
| D1 | Real local stack, `local_only` | **Real-verified** | `tests/integration` 2/2 passed; egress loopback-only. Backend `check_all(deep=True)`: Whisper ok, Ollama generating, no route warnings. |
| D2 | End-to-end over HTTP (real backend process) | **Real-verified** | upload WAV → 409 before confirm → confirm → queued `/process` → poll → `transcribed` (7 timestamped segments, rules + Ollama items) → `/review`. |
| D3 | Hearings persistence (ADR-012 option a) | **Tested + real-verified** | Hearings/candidates/confirmations in the workspace snapshot (store.json, or Postgres via `DATABASE_URL`). Real restart kept status `reviewed`, matter link, session transcript, proceedings. In-flight jobs become `error: interrupted by restart`. |
| D4 | Production per-org hearings (ADR-012 option b) | **Done** | `production_hearings` service/router; webhook org map; frontend `/production/hearings` |
| D5 | Whisper language safeguards | **Tested + real-measured** | Legal prompt English-only (Kiswahili WER 0.77 → 0.66 without it, and it was echoed as text); ≥5-word prompt echo dropped; auto-detect restricted to `en,sw`. |
| D6 | PyAV pin | **Real-verified** | `av<15` — faster-whisper 1.2.1 fails on every file with PyAV 19. |
| D7 | Proceedings grounding hardening | **Tested** (from real model output) | Schema placeholders echoed by qwen2.5:3b rejected; copied `[n] (mm:ss) Speaker:` prefixes tolerated only if the rest matches verbatim. |
| D8 | Ollama client | **Tested + real-verified** | `OLLAMA_TIMEOUT_S` (default 600; was hard-coded 120 and timed out on CPU); JSON mode for action detection; error text keeps the exception type. |
| D9 | Tracker UI fixes | Typechecked, **not browser-tested** | Process only with a recording; queue + poll (no long blocking request); reject; ambiguity warning; matter names; pipeline state/errors; EN/SW language hint. |
| D10 | Diarization | **Not run** | `HF_TOKEN` exists in `.env.local`, but pyannote + torch need ~2 GB and PyPI ran at ~80 KB/s here. |
| D11 | Zoom / Teams live | **Contract-tested only** | No sandbox tenants. |

## Close Open Gaps (2026-11-23)

| Item | Status | Notes |
| --- | --- | --- |
| ADR-012 (a) audit | **Done** | Persistence paths + docs |
| ADR-012 (b) production hearings | **Done** | `/production/hearings`, RLS-scoped repo, webhook tenancy |
| Durable `/process` queue | **Superseded by E3** | Trigger relay alone left demo/local_only in-process, and production in-process jobs stuck `queued` after a restart |
| Live bots (2C) | **Done (contract)** | ADR-015; 1B live join pending credentials |
| Verification 1A | **Done** | `verification/` harnesses + scripts |
| Verification 1B | **Blocked** | No Zoom/Teams/Kiswahili credentials provided this run — not marked verified |

## Production hearings, job queue, Tracker click-through (Claude Code, 2026-11-23)

Review of the Close Open Gaps commit (`5a3a2e9`) found production hearings unusable end to end and the `/process` queue not durable. Fixed:

| # | Item | Status | Evidence / gap |
| --- | --- | --- | --- |
| E1 | `GET /production/hearings` reachable | **Fixed, tested** | Was captured by `production_sessions` `GET /production/{session_id}` → 422 (routers mounted in the wrong order). Hearings/matters/contacts routers now mount first. `test_list_routes_are_not_captured_by_session_routes`. |
| E2 | Production matters + contacts | **Done, tested (fake Supabase)** | `/production/matters`, `/production/contacts` (`production_matters.py`). Without them no org had matters, so no hearing could ever be confirmed. Visibility follows the `haki_matters` RLS policy (matter members + owners/admins); creator gets a matter membership; cross-org ids → 404. Frontend `listMatters/createMatter/*Contact` switch on `VITE_PRODUCTION_AUTH`. |
| E3 | Durable `/process` job queue (ADR-016) | **Done, tested + real-process verified (demo)** | `hearing_jobs.py`: job rows (demo snapshot / `haki_hearing_jobs`), lease + heartbeat, reclaim after a dead worker, retry transient failures (max 3), no retry for `PipelineError`, one active job per hearing. Real restart: a job left `running` by a killed backend resumed automatically (attempt 2 → done). Production claim SQL verified on Postgres 17 (PGlite); no live Supabase run. |
| E4 | Production re-process duplicated sessions/segments | **Fixed, tested** | Pipeline saved a stale hearing copy, wiping `session_id`; segments were appended on every run. Now re-reads before saves and replaces segments (batched inserts). |
| E5 | Deployment-wide connectors in multi-tenant production | **Fixed, tested** | Calendar/Teams/Zoom import, fetch and live capture used one server-wide account for every org. Now only `HAKISCRIBE_INTEGRATIONS_ORGANISATION_ID` may use them (403 otherwise). Per-org OAuth connections: **not implemented**. |
| E6 | `/internal/*` without a secret in production | **Fixed, tested** | Fails closed (503). `/internal/process-hearing` now takes only `job_id`; org/workspace/user come from the job row. |
| E7 | Tracker UI in a browser | **Verified (headless Edge, demo mode)** | Login → add manual hearing → candidates (93%, case ref match) → confirm → VTT upload → process (queued job + poll) → proceedings (rules: 12 Mar 2025, quote-grounded) → reviewed → open session. No console errors. Not run: audio upload (Whisper off), production-mode UI (no Supabase project here). |
| E8 | External HakiChain WorkSpace hearing-pack filing | **Done (code + unit tests)** | `hearing_filing.py`: after `/review`, `POST …/hearings/{id}/file` (demo + production) runs `file_matter` → transcript + proceedings `file_document` → next-date `file_reminder`, then `mark_filed`. Tracker “File to HakiChain” / “Open WorkSpace”. `tests/test_hearing_filing.py`. Live ingress with a real `hkc_` token: **not run** here. |
| E9 | Bidirectional HakiChain alignment Phase 1 (1B) | **Done (code)** | Contract `2026-11` ([12](./12-hakichain-integration-contracts.md)). Ingress: `list_matters` / `get_matter` / `link_matter` / `upsert_hearing` / `finalize_transcript` + `hakiscribe_hearings` migration. Scribe: matter FKs, link APIs, Tracker picker, filing prefers finalize. HC Workspace Hearings tab. Checklist: `verification/hakichain-alignment-checklist.md`. Live deploy + `hkc_` proof: **pending**. |

## Frontier / hybrid invariants

- [x] Default mode is `cloud` (verified via `/health` after Stage B)
- [x] No frontier provider removed; `cloud` NIM→OpenRouter fallback behaviour unchanged (now logged)
- [x] `local_only` blocks cloud: `extract(provider="openrouter")` → `blocked_by_ai_mode` (tested)
- [x] Hybrid fallback still requires `HAKISCRIBE_HYBRID_FALLBACK=explicit_allow` (tested matrix)
- [x] Ambiguous / high-confidence matches still require human confirm; re-import no longer undoes it
