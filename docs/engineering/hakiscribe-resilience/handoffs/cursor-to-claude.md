# Handoff: Cursor → Claude Code (Stage A complete)

## What was inspected

- FastAPI + TanStack Start stack; ASR/LLM abstractions; Nebius/OpenRouter/connectors; HakiChain ingress; Google Calendar OAuth; no prior local Whisper/Compose/Teams/Zoom meeting paths.

## What Cursor implemented (Stage A)

### Documentation

- `docs/engineering/hakiscribe-resilience/` pack (README, 01–10, handoffs)
- Indexed from `docs/README.md`

### AI modes (frontier preserved)

- `hakiscribe-backend/app/services/ai_mode.py` — `cloud|hybrid|private|local_only`, hybrid `HAKISCRIBE_ROUTE_*`, fail-closed allowlists
- `inference_health.py`, `ollama_client.py`
- `LocalWhisperProvider` + mode-aware `get_provider()` in `transcription.py`
- NIM/OpenRouter fallback **disabled** when mode forbids cloud
- Detect/generate route through `ai_mode.resolve_llm_provider` (Ollama path added)
- Tavily gated by research route; Trigger.dev skipped in `local_only`
- `GET/PUT /integrations/ai-mode`; `/health` + `/integrations/compute` include mode/inference
- Env keys in `hakiscribe-backend/.env.example`

### Compose

- `deploy/local-inference/` — CPU/GPU profiles, faster-whisper server, Ollama, optional vLLM

### Virtual court foundations

- Migration `003_hearings_matter_resolution.sql`
- `matter_resolution.py`, `hearings.py`, `routers/hearings.py`
- Adapters: `court_adapters/{calendar,teams,zoom}_adapter.py`
- OAuth: `teams_graph`, `zoom` in `oauth.py` + connector registry + verifiers

### Frontend

- Settings → **AI mode** (`cloud/hybrid/private/local_only` + hybrid routes)
- Tracker → hearings pending confirm + manual/calendar import
- API client methods in `src/lib/hakiscribe.ts`

### Tests run

```text
pytest tests/test_ai_mode.py tests/test_matter_resolution.py tests/test_nebius_privilege.py tests/test_tray_logic.py
→ 23 passed
```

Re-run before starting Stage B if the tree has changed.

## Files created / modified (primary)

**Created**

- `docs/engineering/hakiscribe-resilience/**`
- `deploy/local-inference/**`
- `hakiscribe-backend/app/services/ai_mode.py`
- `hakiscribe-backend/app/services/inference_health.py`
- `hakiscribe-backend/app/services/ollama_client.py`
- `hakiscribe-backend/app/services/matter_resolution.py`
- `hakiscribe-backend/app/services/hearings.py`
- `hakiscribe-backend/app/services/court_adapters/**`
- `hakiscribe-backend/app/routers/hearings.py`
- `hakiscribe-backend/migrations/003_hearings_matter_resolution.sql`
- `hakiscribe-backend/tests/test_ai_mode.py`
- `hakiscribe-backend/tests/test_matter_resolution.py`

**Modified**

- `transcription.py`, `action_detector.py`, `generation.py`, `tavily.py`, `trigger_client.py`, `main.py`, `integrations.py` (router + catalog), `oauth.py`, `schemas.py`, `.env.example`, `migrations/README.md`
- `src/lib/hakiscribe.ts`, `workspace-settings.ts`, `settings.tsx`, `tracker.tsx`, `docs/README.md`

## Outstanding for Claude Code (Stage B)

1. Harden faster-whisper / WhisperX (VAD, diarization, EN/SW legal lexicon)
2. Deep Zoom/Teams **recording download** where official APIs + consent allow
3. Live meeting bots **only** if authorized APIs support them — do not fabricate
4. Proceedings intelligence extraction with quote/timestamp grounding
5. Persist hearing recordings to S3/volumes; production RLS path for hearings tables
6. Optional hybrid fallback logging into `ai_runs` when `HAKISCRIBE_HYBRID_FALLBACK=explicit_allow`
7. E2E against sandbox Zoom/Teams/Calendar accounts

## Invariants — do not break

- Default mode remains **`cloud`**; frontier connectors stay first-class
- Do **not** remove Anthropic / OpenAI / Gemini / Groq / Mistral / OpenRouter / Nebius / `claude_custom` / NIM
- Do **not** collapse `hybrid` into `local_only`
- No silent cloud↔local swap without explicit fallback policy
- Ambiguous matter matches require human confirm — never silent attach
- No destructive git history rewrites (Lovable)

## Migrations

- `003` written; **not** auto-applied. Apply manually on Supabase when enabling production tenancy.
- Demo mode uses in-memory `hearings.py` — no migration required for local demo.

## Uncommitted work

- All Stage A changes are local working tree until the user requests a commit.
