# 01 — Current architecture (verified Stage A)

## Stack

| Layer | Technology | Location |
| --- | --- | --- |
| Frontend | TanStack Start + React 19 + Vite | `src/` |
| Frontend hosts | Lovable (Cloudflare nitro) + optional Vercel | dual deploy, no `vercel.json` unless required |
| API | FastAPI | `hakiscribe-backend/app/` |
| API host | Render Blueprint | `render.yaml` |
| Jobs | Trigger.dev (optional) or in-process | `src/trigger/`, `hakiscribe-backend/trigger/` |
| Storage default | In-memory + JSON | `app/services/storage.py` |
| Storage optional | Postgres (`DATABASE_URL`), S3 drafts | `migrations/`, `object_store.py` |
| Auth default | Shared workspace + bearer | `auth.py` |
| Auth optional | Supabase production tenancy | `production_auth.py`, `001_tenant_security.sql` |

## AI pipeline (pre–Stage A)

```
Mic WebSocket / Omi webhook
  → ASR (TranscriptionProvider): openrouter|groq|openai|intron|nvidia_nim
  → privilege redaction
  → Detect (Nebius Super | OpenRouter)
  → Generate / Ask / Research (frontier connectors + Tavily/Exa)
  → optional HakiChain / Ambiguous / OAuth export
```

## Key modules

- ASR factory: `hakiscribe-backend/app/services/transcription.py`
- LLM select: `hakiscribe-backend/app/services/nebius.py` (`select_provider`)
- Connectors / Ask: `hakiscribe-backend/app/services/integrations.py`, `chat.py`
- HakiChain ingress: `hakiscribe-backend/app/integrations/hakichain_client.py`
- Health: `GET /health`, `GET /models` in `app/main.py`

## Gaps addressed by this initiative

- No `local_only` / `hybrid` mode
- No local Whisper / Ollama first-class path
- No Docker Compose for inference
- No dedicated diarization model
- No virtual court meeting connectors (Teams/Zoom)
- Matter matching is substring client-name only
