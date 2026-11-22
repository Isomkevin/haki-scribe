# 09 — Testing and verification

## Results at end of Stage D (2026-11-23, Windows 11, i5-8250U, 16 GB, no GPU)

| Suite | Command | Result |
| --- | --- | --- |
| Backend, all | `cd hakiscribe-backend && python -m pytest -q` | **99 passed, 2 skipped** (skips = opt-in integration) |
| Frontend unit | `npx vitest run` | 22 passed |
| Frontend typecheck | `npx tsc --noEmit` | Only the 2 pre-existing errors (`contact.tsx`, `privacy.tsx`) |
| Real local stack | `HAKISCRIBE_IT_LOCAL=1 OLLAMA_MODEL=qwen2.5:3b LOCAL_WHISPER_BASE_URL=http://127.0.0.1:8001 HAKISCRIBE_IT_AUDIO=<hearing_en.wav> HAKISCRIBE_IT_AUDIO_EXPECT=adjourned,March pytest tests/integration -v -s` | **2 passed**, `local_only`, egress hosts `['127.0.0.1']` only |
| Deep health | `inference_health.check_all(deep=True)` in `local_only` | Whisper ok, Ollama `generation.ok=true`, `route_warnings=[]` |
| HTTP end-to-end + restart | Real backend process (temp store), real Whisper + Ollama | upload → 409 before confirm → confirm → queued process → `transcribed` (7 segments) → reviewed; after restart: status, matter link, session transcript, proceedings all present |

Real-stack runs use: Ollama 0.40.16 + `qwen2.5:3b`; faster-whisper 1.2.1 `small` int8 in a native venv (`%LOCALAPPDATA%\HakiScribe\wv`), PyAV 14.2.

### Measured quality

**English (synthetic TTS hearing, 33 s):** all 7 segments correct, apart from "Acme" → "Akmee". Rules caught `2025-03-12 hearing` every run. qwen2.5:3b quality varied between runs: one run grounded only "Costs in the cause"; later runs (after the grounding fixes) grounded the outcome, order, direction and appearance. Expect a human to correct a 3B model.

**Kiswahili (6 clips from Google FLEURS `sw_ke` dev, 122 reference words — read speech, not court audio):**

| Config | WER | Notes |
| --- | --- | --- |
| `small`, `language=sw`, built-in legal prompt (Stage B default) | 0.770 | Prompt emitted verbatim as one clip's transcript; "Kenyan" prepended to another |
| `small`, `language=sw`, no prompt | **0.664** | Shipped default for Kiswahili |
| `small`, auto-detect | 0.689–0.730 | One clip detected as Javanese before the `en,sw` constraint; still wrong (en) after it |

Conclusion: `small` on CPU is **not adequate for a Kiswahili court record**. Errors are mostly word segmentation ("pianimto" for "pia ni mto"). Next: measure `large-v3` (needs ≥3 GB disk, slower on CPU) and Intron Sahara (hybrid route) on the same clips; get consented court audio.

### Real-run defects found and fixed in Stage D

| Defect (seen only against real services) | Fix | Regression test |
| --- | --- | --- |
| Every transcription failed: `open() got an unexpected keyword argument 'metadata_errors'` (PyAV 19) | `av>=11,<15` in requirements | real run |
| Server returned 422 for its own bugs; backend error said only "422" | 422 only for PyAV decode errors, else 500; backend includes server detail | contract tests |
| Legal prompt echoed as transcript; raised Kiswahili WER | Prompt only for explicit `WHISPER_LEGAL_PROMPT_LANGS` (default `en`); ≥5-word echo segments dropped | `test_legal_prompt_applies_only_to_explicit_english`, `test_prompt_echo_segments_dropped` |
| Auto-detect picked Javanese for Kiswahili | `WHISPER_ALLOWED_LANGUAGES=en,sw`; forced language never gets the English prompt | `test_auto_detect_constrained_to_allowed_languages` |
| Ollama proceedings call timed out at hard-coded 120 s; error text empty | `OLLAMA_TIMEOUT_S` (default 600); error keeps exception type | `test_default_timeout_suits_cpu_inference` |
| 3B model returned schema placeholder text ("what happened at this sitting") with a real quote → shown as grounded | Placeholder items → `ungrounded` | `test_schema_placeholders_rejected_even_with_real_quote` |
| Model copied `Court:` speaker label into quotes → real quotes rejected | Strip a copied line/speaker prefix; remainder must still match verbatim | `test_copied_line_prefix_is_tolerated_but_remainder_must_match` |
| Malformed JSON from local model crashed action detection (demo library at startup) | Ollama JSON mode for detection | `test_json_mode_requests_json_object` + real run |

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

Stage B blockers 1–2 were resolved in Stage D (see top); 3–4 still apply.

## Still to verify (with what)

| Check | Needs |
| --- | --- |
| Local LLM quality with a larger model | ≥8B model with enough free RAM (gemma4 is pulled but needs ~10 GB free); compare against qwen2.5:3b on the same transcript |
| Kiswahili with `large-v3` / Intron Sahara | ≥3 GB free disk for large-v3; Intron key for hybrid; re-run the FLEURS WER script, then real court audio |
| Kiswahili / code-switch on court audio | Real consented Kiswahili hearing recordings + reference transcripts (WER) |
| Docker image with the new server | Docker Desktop running; `docker compose --profile cpu up -d --build` |
| Tracker UI in a browser | Frontend + backend running; click through import → confirm → upload → process → review |
| Diarization | `WITH_DIARIZATION=1` image, `HF_TOKEN`, multi-speaker audio |
| Zoom recording + webhook | Zoom Marketplace app (OAuth + Event Subscriptions), host with cloud recording, public HTTPS URL for the webhook |
| Teams transcript/recording | Entra app with admin-consented `OnlineMeetingTranscript.Read.All` / `OnlineMeetingRecording.Read.All`; meeting organised by the signed-in user with transcription on |
| Google Calendar import | Connected Google account (Stage A path; unchanged) |
| No-egress proof at network level | Run integration tests in a container with egress firewalled (current proof is at the httpx layer) |

## Regression (unchanged from Stage A plan)

- `cloud` mode detect/generate/Ask with Nebius or OpenRouter
- Connector cards still connect Anthropic/OpenAI/Gemini
- Trigger.dev path when keyed (cloud/hybrid only)

## Close Open Gaps — verification harnesses (1A / 1B)

### 1A entry points (shipped)

| Entry | Path |
| --- | --- |
| Overview | `docs/engineering/hakiscribe-resilience/verification/README.md` |
| Zoom/Teams checklist | `verification/zoom-teams-checklist.md` |
| Kiswahili ASR checklist | `verification/kiswahili-asr-checklist.md` |
| Court sandbox script | `hakiscribe-backend/scripts/verify_court_adapters_sandbox.py` (opt-in `HAKISCRIBE_VERIFY_ZOOM` / `TEAMS`) |
| WER script | `hakiscribe-backend/scripts/verify_asr_wer.py` (opt-in `HAKISCRIBE_VERIFY_ASR`) |
| Contract tests | `tests/test_production_hearings.py`, `tests/test_live_bots.py` |

### 1B live runs (credentials required)

| Run | Result (2026-11-23) |
| --- | --- |
| Zoom sandbox E2E | **Not run** — no sandbox tenant / OAuth credentials provided |
| Teams sandbox E2E | **Not run** — no Graph admin-consent tenant provided |
| Kiswahili WER (`large-v3` / Sahara) | **Not run** — no consented court audio / model download this session |
| Live bot join | **Not run** — Teams bot / Zoom Meeting SDK credentials not provided |

Do **not** mark Zoom/Teams/Kiswahili/bots verified until 1B evidence is pasted here.
