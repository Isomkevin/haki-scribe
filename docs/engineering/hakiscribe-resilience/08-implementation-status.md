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
| 1 | Local LLM (Ollama) for proceedings / detect | Code: done. **Real generation: Blocked** | Host Ollama 0.40.16 has no `llama-server` runner (interrupted auto-update) → every generation 500s. Integration test reached it, got the 500, reported `llm.status=error`, and made **only loopback calls**. |
| 2 | Ollama readiness | **Tested + real-verified** | `check_ollama(deep=True)` 1-token probe; against the broken host install it correctly reports `ok=false` where the shallow probe said `ok=true`. `model_available` flags un-pulled `OLLAMA_MODEL`. |
| 3 | faster-whisper server hardening (verbose_json, VAD params, EN/SW legal prompt, `/ready`, threadpool, Windows-safe temp file) | **Contract-tested** | Real `server.py` loaded with a stub `WhisperModel`; backend client → server over ASGI. **Real model run: Blocked** (C: drive had 76 MB free; Docker daemon not running). |
| 4 | Diarization (pyannote, opt-in) | Code: done. Speaker assignment **tested**. **pyannote run: Not run** | Needs `WITH_DIARIZATION=1` build, `HF_TOKEN` with pyannote terms accepted, ~2 GB. Disabled path reports the reason instead of inventing speakers. |
| 5 | Platform speaker labels (Teams/Zoom WebVTT) | **Tested** | `vtt.py`; Teams `<v Name>` and Zoom `Name:` dialects. |
| 6 | EN/SW transcription | EN/SW **text** handling tested. **Kiswahili audio accuracy: Blocked** | No real Kiswahili recordings in repo; this host only has English TTS voices. Synthetic EN hearing WAV was generated but could not be transcribed (item 3). |
| 7 | Proceedings intelligence with quote grounding | **Tested** (LLM mocked) | Rules (EN+SW, no AI) + LLM extraction; items without a verbatim transcript quote → `ungrounded`; privileged lines never reach the prompt; stale provenance bug avoided. |
| 8 | Hybrid fallback logging (`ai_runs`) | **Tested** | `cloud_fallback_allowed` / `record_fallback`; NIM→OpenRouter in ASR and generation. |
| 9 | Zoom: recording download + `recording.completed` webhook | **Contract-tested** | Signature + replay window + URL validation + download with `download_token`. **No real Zoom tenant used.** |
| 10 | Teams: transcript / recording via Graph | **Contract-tested** | JoinWebUrl → onlineMeeting → transcripts (VTT) → fallback recordings; actionable 403/404 errors. **No real tenant used.** OAuth scopes extended. |
| 11 | Live meeting bots | **Not implemented** (by decision) | No official API path without Teams calling-bot / Zoom Meeting SDK registration — see ADR-004/010. |
| 12 | Recording persistence | **Tested** (local volume) · S3 mirror **Not run** | Fixes Stage A bug: `/upload` discarded bytes (`object_store.put_bytes` did not exist). Path-traversal-safe keys; size cap. |
| 13 | Matter Resolution Engine | **Tested** | Canonical Kenyan case refs (`E045 of 2024` = `E45/2024`), boundary-safe matching, conflicting-case-number penalty, near-tie ambiguity. |
| 14 | Hearing lifecycle | **Tested** | Explicit transition table; fixes Stage A bug where re-importing a calendar/Teams/Zoom event reset human confirmations; matter link locked after capture; idempotent session creation. |
| 15 | Post-hearing pipeline (`/process`) | **Tested** (`wait=true`, VTT path and stub-Whisper path) · background mode **Not run** under test | Refuses before human confirm; `transcribed` then human `/review`. |
| 16 | Frontend API client for new endpoints | Done, typechecked | `src/lib/hakiscribe.ts`. |
| 16b | Tracker UI wired to Stage B lifecycle | **Done (Stage C connection)** | Upload recording/VTT, Teams/Zoom fetch, process (`wait=true`), proceedings (grounded + ungrounded), review; Calendar/Teams/Zoom import; Settings deep local probe. |

## Stage C connection pass (Cursor)

| Item | Status | Notes |
| --- | --- | --- |
| Backend Stage B verification | done | `pytest` → **88 passed, 2 skipped** |
| Frontend vitest | done | **22 passed** |
| Tracker ↔ hearings pipeline | done | Full match → ingest → process → review UI |
| AI mode Settings ↔ deep probe | done | `getAiMode(true)` → Ollama generation probe |
| ADR-012 hearings persistence | still open | In-memory demo only; not blocking Stage B UI connection |
| 17 | Production persistence for hearings (migration 003 repository, RLS path) | **Not implemented** | Hearings are in-memory; router + webhook mounted only when production auth is off. See ADR-012. |
| 18 | Real-stack integration tests | Written, **skipped by default** | `tests/integration/test_local_stack.py` (`HAKISCRIBE_IT_LOCAL=1`). Includes no-egress assertion. |

## Frontier / hybrid invariants

- [x] Default mode is `cloud` (verified via `/health` after Stage B)
- [x] No frontier provider removed; `cloud` NIM→OpenRouter fallback behaviour unchanged (now logged)
- [x] `local_only` blocks cloud: `extract(provider="openrouter")` → `blocked_by_ai_mode` (tested)
- [x] Hybrid fallback still requires `HAKISCRIBE_HYBRID_FALLBACK=explicit_allow` (tested matrix)
- [x] Ambiguous / high-confidence matches still require human confirm; re-import no longer undoes it
