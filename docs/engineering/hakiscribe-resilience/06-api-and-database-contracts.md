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
