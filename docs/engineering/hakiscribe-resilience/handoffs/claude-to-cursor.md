# Handoff: Claude Code → Cursor

## Stage D update (2026-11-23, on top of `2cf89e0`) — uncommitted working-tree changes

**1. Completed.** The real local stack now works on the reference host and is verified end to end. Ollama was repaired (CPU runner restored) and runs `qwen2.5:3b`; faster-whisper `small` runs in a native venv. Hearings persistence (ADR-012 option a) is done. Fixed the defects that only real runs exposed: PyAV pin, Whisper prompt echo and language safeguards (ADR-013), Ollama timeout and JSON mode (ADR-014), proceedings placeholder and prefix grounding. Tracker fixes: process gating, queue + poll, reject, ambiguity warning, matter names, pipeline state, EN/SW selector.

**2. Files.** `deploy/local-inference/{README.md,.env.example,docker-compose.yml}`, `faster-whisper/{server.py,requirements.txt}`; `hakiscribe-backend/.env.example`, `app/services/{action_detector,hearings,ollama_client,proceedings_intel,storage,transcription}.py`; tests `test_hearing_persistence.py` (new), `test_inference_orchestration.py`, `test_local_whisper_contract.py`, `test_proceedings_intel.py`; `src/components/hakiscribe/tracker.tsx`; docs 08/09/10 + this file.

**3. Migrations.** None. Hearings ride on the existing storage snapshot (store.json / `DATABASE_URL` snapshot table).

**4. Interface changes.** Whisper `verbose_json` adds `prompt_applied`, `prompt_echo_dropped`, `language_forced_from`. New env: `WHISPER_ALLOWED_LANGUAGES` (default `en,sw`), `WHISPER_LEGAL_PROMPT_LANGS` (default `en`), `OLLAMA_TIMEOUT_S` (default 600). The server returns 500 (was 422) for non-decode failures. `ollama_client.complete(json_mode=...)`. The Tracker now calls `/process` without `wait` and polls `/proceedings`.

**5. Tests.** Backend 99 passed / 2 skipped; vitest 22; tsc only the 2 pre-existing errors. Real-stack integration 2/2 passed (loopback-only). HTTP end-to-end plus real restart passed. Kiswahili WER measured (09).

**6. Known issues.** Kiswahili with `small` WER ≈ 0.66 — not record-grade. 3B extraction quality is inconsistent. Tracker changes not browser-tested. Docker image not rebuilt. The next Ollama auto-update needs ≥6 GB free or it breaks again. Running the backend in `local_only` makes demo-library seeding call the local LLM at startup (slow on CPU, but non-blocking).

**7. Outstanding.** ADR-012 (b), production per-org hearings. Kiswahili with `large-v3` / Intron Sahara. Diarization run. Zoom/Teams sandbox runs. Job queue for `/process`.

**8. Dependencies.** Free disk (≥3 GB for large-v3, ≥6 GB for Ollama updates); Docker Desktop; Zoom/Entra apps; consented court audio.

**9. For Cursor.** `pytest -q` → 99 passed, 2 skipped. Click through the Tracker in a browser against a `local_only` backend. Keep the language selector, because explicit `sw` beats auto. Don't re-enable the legal prompt for Kiswahili without re-measuring (ADR-013).

---

## Stage B (2026-11-22)

Built on Stage A commit `a9f3db3`; later committed by the owner as `371ad13` / `2cf89e0`.

Status detail: [08](../08-implementation-status.md) · test evidence: [09](../09-testing-and-verification.md) · decisions: [10](../10-decisions-and-risks.md) ADR-006…012 · contracts: [06](../06-api-and-database-contracts.md) "Stage B additions".

## 1. Completed by Claude Code

- **Local Whisper server**: `verbose_json` timestamped segments, language + duration, configurable VAD, built-in EN/SW court-vocabulary prompt, `/ready` preload, transcription off the event loop, Windows-safe temp files. `json` response unchanged for live captions.
- **Diarization** (opt-in pyannote) with honest "disabled because …" reporting; speaker assignment by max overlap.
- **Backend full-file ASR**: `LocalWhisperProvider.transcribe_file` (keyword shape matches Intron's).
- **Platform transcripts**: WebVTT parser for Teams `<v Name>` and Zoom `Name:`.
- **Proceedings intelligence**: rules (EN + Kiswahili) + mode-routed LLM, strict quote grounding, `ungrounded` bucket, `ai_runs` metadata row.
- **Orchestration**: centralised cloud-fallback policy + `ai_runs` fallback logging (Cursor outstanding #6); Ollama `model_available` + `?deep=true` generation probe; route warnings.
- **Zoom**: recording download (audio → transcript fallback), signed `recording.completed` webhook with URL validation, replay window, fail-closed.
- **Teams**: JoinWebUrl → onlineMeeting → transcript (VTT) → recording fallback; actionable 401/403/404 errors; OAuth scopes extended.
- **Ingestion**: recording bytes actually persisted (Stage A dropped them), sanitised keys, size cap, S3 mirror.
- **Matter Resolution Engine**: canonical Kenyan case references, boundary-safe matching, case-number conflict penalty, near-tie ambiguity.
- **Lifecycle**: explicit transition table; re-import no longer erases confirmations; matter link locked after capture; idempotent sessions; human `/review`.
- **Post-hearing pipeline**: `/process` (background or `wait=true`) → session transcript → proceedings record → `transcribed`.
- **Frontend client** methods + types (no UI).

### Stage A bugs fixed (behaviour changes)

| Bug | Fix |
| --- | --- |
| `/hearings/{id}/upload` discarded bytes (`object_store.put_bytes` didn't exist; error swallowed) | `recording_store` + real `object_store.put_bytes/get_bytes` |
| Re-import / `/match` reset `matched`/`rejected` hearings to `pending_confirm` and cleared `matter_id` | `propose_matches` only moves `scheduled|pending_confirm` |
| Case ref `12` matched `Petition 120/2023` (substring) | boundary-aware + canonical refs |
| `create_session_from_hearing` created a duplicate session per call | idempotent |
| `tracker.tsx` TS2379 under `exactOptionalPropertyTypes` | widened `importManualHearing` body type |
| NIM generation never set `_last_completion` (provenance) | set on success |

## 2. Files

**Created**
- `deploy/local-inference/faster-whisper/diarize.py`, `requirements-diarization.txt`
- `hakiscribe-backend/app/services/{hearing_pipeline,proceedings_intel,recording_store,vtt}.py`
- `hakiscribe-backend/app/routers/court_webhooks.py`
- `hakiscribe-backend/tests/{stage_b_helpers,test_vtt,test_hearing_lifecycle,test_proceedings_intel,test_court_adapters,test_inference_orchestration,test_local_whisper_contract}.py`
- `hakiscribe-backend/tests/integration/{__init__,test_local_stack}.py`

**Modified**
- `deploy/local-inference/{.env.example,README.md,docker-compose.yml}`, `faster-whisper/{Dockerfile,server.py}`
- `hakiscribe-backend/.env.example`, `app/main.py`, `app/routers/{hearings,integrations}.py`
- `app/services/{ai_mode,generation,hearings,inference_health,matter_resolution,oauth,object_store,transcription}.py`
- `app/services/court_adapters/{__init__,base,teams_adapter,zoom_adapter}.py`
- `src/lib/hakiscribe.ts`
- Docs: `06` (appended), `08`, `09` (rewritten), `10` (appended), this file

Note: `deploy/local-inference/.env.example` was overwritten before being read; diffed against `a9f3db3` afterwards — strict superset, no values lost.

## 3. Database migrations

None. Stage B uses existing migration-003 columns (`platform_metadata`, `recording_object_key`). Migration 003 is still not wired to a repository — see ADR-012.

## 4. API / interface changes

See 06 "Stage B additions". Breaking-ish: `/confirm` now 409s once capture started; `/upload` 409s on transcribed+ hearings; `/match` no longer un-confirms. `court_adapters.base` adds `AdapterError`, `HearingArtifact`, `http_client`, `CourtAdapter.fetch_artifact`.

## 5. Tests executed

- Backend: **88 passed, 2 skipped** (Stage A baseline was 35 passed). Frontend: vitest 22 passed; tsc only the 2 pre-existing route errors.
- Real Ollama integration: **failed due to host** (`llama-server binary not found`); egress stayed loopback-only.
- Real faster-whisper: **not run** (disk full).
- Zoom/Teams: **contract tests only**, no real tenants.

## 6. Known issues

- Hearings are in-memory (lost on restart); hearings router + Zoom webhook only in demo mode (ADR-012).
- `/process` background mode not exercised by tests; in-process tasks die with the worker.
- Zoom `download_token` header form unverified live (10, risks).
- Kiswahili ASR accuracy completely unverified.
- `datetime.utcnow()` deprecation warnings (pre-existing pattern, kept for consistency).

## 7. Outstanding

1. Decide and implement ADR-012 (hearings persistence / production routers).
2. ~~Tracker UI: upload / process / proceedings / review~~ — **done in Stage C connection pass** (`tracker.tsx` + `hakiscribe.ts` Teams/Zoom import + `wait=true` process).
3. Real-stack runs listed in 09 "Still to verify".
4. Job queue for `/process` if long recordings are expected in production.
5. Live meeting capture only if the owner wants to register a Teams calling bot / Zoom Meeting SDK app.

## 8. External dependencies and credentials

| Need | For |
| --- | --- |
| ≥ 0.5 GB free disk (≥ 3 GB for large-v3) and/or Docker Desktop running | Local Whisper |
| Repaired Ollama install (rerun installer); `OLLAMA_MODEL` set to a pulled model (`gemma4` is present) | Local LLM |
| `HF_TOKEN` with pyannote terms accepted; `WITH_DIARIZATION=1` build | Diarization |
| Zoom Marketplace OAuth app (recording scopes) + Event Subscriptions secret + public HTTPS backend URL | Zoom |
| Entra app, admin consent for `OnlineMeetingTranscript.Read.All` / `OnlineMeetingRecording.Read.All` | Teams |
| Consented real EN + Kiswahili court recordings with reference transcripts | Accuracy / WER |

## 9. Instructions for Cursor Stage C

1. `git diff a9f3db3` — review against 06/10; Stage A behaviour changes are listed in §1.
2. `cd hakiscribe-backend && python -m pytest -q` → expect 88 passed, 2 skipped.
3. Check `GET /health` still shows `ai_mode.mode == "cloud"` with no env overrides.
4. With a working Ollama: `curl ".../integrations/ai-mode?deep=true"`, then run `tests/integration` per `deploy/local-inference/README.md` → expect egress loopback only.
5. Wire Tracker UI (outstanding #2) using `api.uploadHearingFile / fetchHearingRecording / processHearing / getHearingProceedings / reviewHearing`.
6. Resolve ADR-012 before claiming production readiness.
7. Do not mark Zoom/Teams "verified" until a sandbox-tenant run is recorded in 09.

## Invariants preserved

- Frontier connectors intact; default `cloud`.
- Hybrid route matrix intact; cross-realm fallback still needs `explicit_allow` and is now logged.
- No silent cloud fallback in `local_only` / `private` (tested).
- No silent matter attach (tested, including after re-import).
- No git history rewritten; nothing committed or pushed by Claude Code.
