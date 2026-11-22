# 09 — Testing and verification

## Results at end of Stage B (2026-11-22, Windows 11, Python 3.12.10)

| Suite | Command | Result |
| --- | --- | --- |
| Backend, all | `cd hakiscribe-backend && python -m pytest -q` | **88 passed, 2 skipped** (skips = opt-in integration) |
| Stage B new tests only | `pytest tests/test_vtt.py tests/test_hearing_lifecycle.py tests/test_proceedings_intel.py tests/test_court_adapters.py tests/test_inference_orchestration.py tests/test_local_whisper_contract.py` | **53 passed** |
| Stage A baseline before Stage B edits | `python -m pytest -q` | 35 passed |
| Frontend unit | `npx vitest run` | 22 passed |
| Frontend typecheck | `npx tsc --noEmit` | 2 errors, both pre-existing in `src/routes/contact.tsx` / `privacy.tsx` (untouched). Stage A error in `tracker.tsx` fixed. |
| Real local LLM | `HAKISCRIBE_IT_LOCAL=1 OLLAMA_MODEL=gemma4 pytest tests/integration -k LocalLlm` | **FAILED — environment**: Ollama returned 500 `llama-server binary not found`. Egress assertion held (only `127.0.0.1`). |
| Real local ASR | `tests/integration -k LocalAsr` | **Not run**: faster-whisper could not be installed (disk full; see below). |

## What each test file proves

| File | Proves | Does not prove |
| --- | --- | --- |
| `test_vtt.py` | Teams/Zoom VTT dialects, BOM/CRLF, NOTE blocks | — |
| `test_hearing_lifecycle.py` | Re-import keeps confirm/reject; illegal transitions; recording-before-confirm; matter lock; idempotent session; case-ref canonicalisation, conflict penalty, ambiguity; recordings traversal/size cap | Postgres persistence |
| `test_proceedings_intel.py` | EN+SW rules (incl. Kiswahili verb prefixes); quote grounding (single + cross-segment); fabricated / privileged quotes rejected; privileged text never in prompt; LLM failure keeps rules + no stale provenance; `local_only` blocks cloud | Quality of a real model's extraction |
| `test_court_adapters.py` | Zoom file choice, Bearer download, signature/replay/URL-validation, webhook ingest leaves matter unconfirmed; Teams transcript-first, 403→recording fallback, organiser error; route flow upload→confirm→process→review | Real Zoom/Graph behaviour, scopes, admin policy |
| `test_inference_orchestration.py` | Fallback matrix across 4 modes; `ai_runs` fallback row; Ollama model-tag matching; route warnings | — |
| `test_local_whisper_contract.py` | Real `server.py` request/response (json/verbose_json/errors/legal prompt/VAD/diarization-disabled reason) and backend → server → pipeline in `local_only` | Transcription accuracy, real faster-whisper |
| `tests/integration/test_local_stack.py` | (When run) real Ollama + real Whisper in `local_only` with **no non-loopback HTTP** | — |

Tests never touch `data/store.json`: `tests/stage_b_helpers.IsolatedStoreTestCase` disables persistence, swaps every store dict, and points recordings at a temp dir.

## Host environment blockers found during Stage B

1. **Disk full**: `C:` had 76 MB free (476 GB volume). faster-whisper install failed with `Errno 28`. The partial venvs created for the attempt were deleted (back to ~249 MB free). Needs ~0.5 GB for faster-whisper + `base` model; large-v3 needs ~3 GB.
2. **Ollama broken**: 0.40.16 → 0.40.17 auto-update left `lib/ollama/` missing. `/api/tags` lists `gemma4` but generation fails. Fix: rerun the Ollama installer.
3. **Docker Desktop daemon not running**, so the Compose stack could not be used either.
4. Windows long paths disabled: deep venv paths fail on numpy's test files (README troubleshooting updated).

## Still to verify (with what)

| Check | Needs |
| --- | --- |
| Local LLM proceedings extraction quality + latency | Working Ollama + a pulled model (`gemma4` is already pulled); run `tests/integration -k LocalLlm -s` |
| Local ASR EN end-to-end + timestamps | ~0.5 GB free; `HAKISCRIBE_IT_AUDIO=<wav>` (a synthetic SAPI hearing WAV is easy to regenerate; real courtroom audio preferred) |
| Kiswahili / code-switch ASR accuracy | Real consented Kiswahili hearing recordings + reference transcripts (WER) |
| Diarization | `WITH_DIARIZATION=1` image, `HF_TOKEN`, multi-speaker audio |
| Zoom recording + webhook | Zoom Marketplace app (OAuth + Event Subscriptions), host with cloud recording, public HTTPS URL for the webhook |
| Teams transcript/recording | Entra app with admin-consented `OnlineMeetingTranscript.Read.All` / `OnlineMeetingRecording.Read.All`; meeting organised by the signed-in user with transcription on |
| Google Calendar import | Connected Google account (Stage A path; unchanged) |
| No-egress proof at network level | Run integration tests in a container with egress firewalled (current proof is at the httpx layer) |
| `/process` background mode | Manual: POST without `wait`, poll `/proceedings` |

## Regression (unchanged from Stage A plan)

- `cloud` mode detect/generate/Ask with Nebius or OpenRouter
- Connector cards still connect Anthropic/OpenAI/Gemini
- Trigger.dev path when keyed (cloud/hybrid only)
