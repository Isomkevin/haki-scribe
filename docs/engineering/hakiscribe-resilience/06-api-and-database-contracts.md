# 06 — API and database contracts

## Environment

| Variable | Values / meaning |
| --- | --- |
| `HAKISCRIBE_AI_MODE` | `cloud` \| `hybrid` \| `private` \| `local_only` (default `cloud`) |
| `HAKISCRIBE_ROUTE_ASR` | Provider id for hybrid ASR |
| `HAKISCRIBE_ROUTE_DETECT` | Provider id for detect |
| `HAKISCRIBE_ROUTE_DRAFT` | Provider id for draft/generate |
| `HAKISCRIBE_ROUTE_ASK` | Provider id for Ask/chat |
| `HAKISCRIBE_ROUTE_RESEARCH` | `tavily_exa` \| `off` \| `local_stub` |
| `HAKISCRIBE_HYBRID_FALLBACK` | empty \| `explicit_allow` |
| `LOCAL_WHISPER_BASE_URL` | e.g. `http://127.0.0.1:8001` |
| `OLLAMA_BASE_URL` | e.g. `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | default chat model id |

## HTTP (Stage A)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Includes `ai_mode`, routes, local probes |
| GET | `/integrations/ai-mode` | Current mode + routes + validation |
| PUT | `/integrations/ai-mode` | Update mode + hybrid routes (demo workspace) |
| GET | `/hearings` | List hearings |
| POST | `/hearings/import/calendar` | Import from Google Calendar |
| POST | `/hearings/import/manual` | Create hearing + optional upload meta |
| POST | `/hearings/{id}/match` | Propose matter matches |
| POST | `/hearings/{id}/confirm` | Confirm/reject matter link |
| POST | `/hearings/{id}/session` | Create session from hearing |
| POST | `/hearings/{id}/upload` | Attach recording bytes/meta |

## Migration `003_hearings_matter_resolution.sql`

Tables (org-scoped when production auth on):

- `haki_hearings` — source, title, starts_at, meeting urls, status, matter_id, session_id, confidence
- `haki_hearing_match_candidates` — hearing_id, matter_id, score, rationale
- `haki_hearing_confirmations` — audit of human confirm/reject

Demo mode mirrors via in-memory store in `hearings.py` / `storage` helpers.

## Stage B additions (Claude Code)

### Environment

| Variable | Values / meaning |
| --- | --- |
| `HAKISCRIBE_RECORDINGS_DIR` | Local recordings volume (default `data/recordings`, gitignored). Always written. |
| `HAKISCRIBE_MAX_RECORDING_MB` | Upload/ingest cap (default `1024`) → HTTP 413 |
| `ZOOM_WEBHOOK_SECRET_TOKEN` | Zoom Event Subscriptions secret. Unset → `/webhooks/zoom` returns 503 for everything |
| `S3_BUCKET` + AWS creds | Optional mirror of recordings (`object_store.put_bytes/get_bytes`) |
| Whisper server: `WHISPER_LEGAL_PROMPT`, `WHISPER_VAD_MIN_SILENCE_MS`, `WHISPER_VAD_SPEECH_PAD_MS`, `DIARIZATION_ENABLED`, `DIARIZATION_MODEL`, `HF_TOKEN` | See `deploy/local-inference/.env.example` |

### HTTP

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/integrations/ai-mode?deep=true` | Adds a 1-token Ollama generation probe (catches listed-but-unloadable models) |
| POST | `/hearings/{id}/upload` | **Changed:** bytes now persist via `recording_store` (Stage A discarded them); filename sanitised; 413 over cap; 409 if hearing already transcribed |
| POST | `/hearings/{id}/transcript` | Attach Teams/Zoom WebVTT instead of audio |
| POST | `/hearings/{id}/fetch-recording?prefer=audio\|transcript` | Pull artifact from Zoom / Teams via official APIs |
| POST | `/hearings/{id}/process?wait=&use_llm=&diarize=&language_hint=` | Transcribe/parse → session transcript → proceedings record. 409 until matter confirmed. Default queues a background task; `wait=true` runs inline |
| GET | `/hearings/{id}/proceedings` | `{status, pipeline, asr, proceedings}` |
| POST | `/hearings/{id}/review` | Human sign-off: `transcribed → reviewed` |
| POST | `/webhooks/zoom` | `endpoint.url_validation` + signed `recording.completed` |
| POST | `/hearings/{id}/confirm` | **Changed:** 409 once capture started (matter link locked) |

### Local Whisper server (`deploy/local-inference/faster-whisper/server.py`)

`response_format=json` (default, unchanged `{text, model}`) | `verbose_json` (`segments[{id,start,end,text,avg_logprob,no_speech_prob,speaker?}]`, `language`, `language_probability`, `duration`, `diarization{enabled, reason|speakers}`, `processing_ms`) | `text`. Form field `diarize_speakers`. `POST /ready` preloads the model.

### Python interfaces

- `LocalWhisperProvider.transcribe_file(audio, *, filename, language_hint, diarize)` — same keyword shape as `IntronVoiceProvider.transcribe_file`; **raises** on failure (live `transcribe_chunk` still degrades to empty text).
- `ai_mode.cloud_fallback_allowed(task)` / `ai_mode.record_fallback(task, from, to)` — single source for NIM→OpenRouter fallback policy; every fallback writes an `ai_runs` row with `status="fallback_from:<provider>"`.
- `CourtAdapter.fetch_artifact(hearing, *, prefer) -> HearingArtifact{kind, filename, data, content_type, metadata}`; `AdapterError(message, status)`; `court_adapters.base.http_client()` (tests inject `_transport`).
- `hearings.transition()` / `ALLOWED_TRANSITIONS` / `InvalidTransition`; `hearings.set_pipeline_state`, `mark_reviewed`, `find_external`, `list_confirmations`.
- `hearing_pipeline.ingest_recording / ingest_transcript / process_hearing`.
- `proceedings_intel.extract(segments, *, use_llm, provider)` → `{rules[], llm{status, items[], ungrounded[], provider, model, ai_mode, latency_ms}, segments_considered, privileged_segments_excluded}`.
- `matter_resolution.canonical_case_refs`, `is_ambiguous`, `AMBIGUITY_MARGIN=0.1`, `CONFLICT_PENALTY=0.4`.

### Database

No new migration. Stage B state lives in existing columns: `haki_hearings.platform_metadata` (jsonb) holds `pipeline`, `asr`, `proceedings`, `recording`, `review`, `match`; `recording_object_key` holds the recordings-store key. **Hearings are still in-memory only** — migration 003 is not wired to a repository (see 10 / ADR-012).
