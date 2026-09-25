# HakiScribe backend

FastAPI service for sessions, live captions, Omi webhooks, Action Tray detect/generate,
connectors (OAuth + LLM keys), research/news (Exa), and workspace sign-in.

## Run it

```
pip install -r requirements.txt
cp .env.example .env.local   # fill in OPENROUTER_API_KEY (captions + detect + draft)
uvicorn app.main:app --reload --port 8000
```

Prefer `.env.local` for secrets (loaded by `app/main.py`). Do not commit keys.

## Deploy on Render

The repo-root `render.yaml` Blueprint deploys this folder as a Python web service.

- Binds to `0.0.0.0:$PORT` (required on Render)
- Health check: `GET /health`
- Root directory: `hakiscribe-backend`
- Storage defaults to in-memory (+ local JSON); set `DATABASE_URL` for Postgres. Free-tier spin-downs still clear ephemeral disk.

Create from the Blueprint (after this file is on `main`):

<https://dashboard.render.com/blueprint/new?repo=https://github.com/Isomkevin/haki-scribe>

Fill `OPENROUTER_API_KEY` when prompted — that is the only required key. Live captions use OpenRouter's speech-to-text endpoint (`openai/whisper-large-v3`); detection and drafting use the same key. Model slugs like `openai/gpt-4o` are OpenRouter IDs, not a second vendor account. Other sponsor keys are optional and fall back to local-only behavior. The Lovable frontend already points at `https://hakiscribe-backend.onrender.com` via the repo-root `.env` (`VITE_API_BASE_URL`).

Everything works with zero sponsor keys configured — Ambiguous AI,
Trigger.dev, and Exa all no-op gracefully and the pipeline falls back to
local-only behavior. Add keys incrementally to light up real integrations.

For Google Drive / Calendar, Dropbox, OneDrive, Gemini Vertex OAuth, and
workspace accounts, see [`docs/CONNECTOR_OAUTH_SETUP.md`](../docs/CONNECTOR_OAUTH_SETUP.md).

## Auth (private workspace)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → `{token, user}` |
| GET | `/auth/demo` | Temporary judging credentials when `DEMO_LOGIN_ENABLED=true` |
| GET | `/auth/me` | Current user from `Authorization: Bearer …` |

Accounts: `HAKISCRIBE_USERS` (`email:password|Display Name`, comma-separated).
`AUTH_SECRET` keeps issued tokens valid across restarts. Demo account:
`DEMO_EMAIL` / `DEMO_PASSWORD` (defaults `demo@hakiscribe.app` /
`hakiscribe-demo`). Set `DEMO_LOGIN_ENABLED=false` before real client work.

Scope today: one shared workspace for all signed-in users (not per-lawyer vaults).

## Quick demo path (fastest to a working end-to-end demo)

1. `POST /sessions` with `{"title": "Demo", "source": "omi", "language_hint": "code-switch"}` -> note the `id`.
2. `POST /webhooks/omi` with that `id` as `session_external_id` and a fake `segments` list (use raw labels like "Speaker 1") to prove ingestion works before touching real Omi payloads.
3. `GET /sessions/{id}` to see the transcript assembled.
4. `POST /sessions/{id}/speakers` with `{"mapping": {"Speaker 1": "John Kamau", "Speaker 2": "Mercy Wairimu"}}` to relabel.
5. `PATCH /sessions/{id}/segments/{segment_id}` with `{"redacted": true}` on any segment that should never reach the detection prompt.
6. `POST /sessions/{id}/flags` with `{"at_ms": 4000, "label": "Follow-up date"}` to simulate the no-look Flag button.
7. `POST /sessions/{id}/finalize` to mark it ready.
8. `POST /sessions/{id}/detect` (needs `OPENROUTER_API_KEY`) — runs the action-tray detection pass, weighted by flags and aware of any existing `Matter` records. Runs via Trigger.dev if `TRIGGER_SECRET_KEY` is set, otherwise directly in-process. If `EXA_API_KEY` is set, named counterparties get enriched with a company lookup.
9. `POST /sessions/{id}/generate` with `{"action_ids": [...]}` — generates the selected ones. `draft_document`, `private_note`, `time_entry` are always real; `calendar_event` always returns a real `.ics`; if `AMBIGUOUS_API_KEY` is set, `draft_document` also creates a real Ambiguous Doc (+ a Chat notification), `calendar_event` also creates a real Ambiguous Calendar event, `workspace_matter` creates/links a real Ambiguous CRM deal, and `crm_entry` attempts a real Ambiguous CRM contact — all fall back to local-only results if that key isn't set. Connected Drive / Dropbox / OneDrive / Google Calendar exports use OAuth tokens stored server-side when those connectors are configured.
10. For mic capture: connect a WebSocket client to `/sessions/{id}/stream` and send raw audio chunk bytes; you'll get `TranscriptSegment` JSON back per chunk.
11. `GET /matters` to see matters created across sessions — run step 8 twice for the same client and watch the second one link instead of duplicating.

## Sponsor integrations at a glance

| Sponsor | Where | Behavior without a key |
|---|---|---|
| OpenRouter | Live captions (`transcription.py`) plus detection + drafting | Captions no-op; `/detect` and `draft_document` fall back to local text |
| OpenAI | Optional direct Whisper if `ASR_PROVIDER=openai`; also Connectors key for Ask | Use OpenRouter (default) or Groq instead |
| Groq | Optional faster Whisper if `ASR_PROVIDER=groq` | Stay on OpenRouter unless you want a dedicated Groq key |
| Ambiguous AI | Docs/Calendar/CRM/Chat (`app/integrations/ambiguous_client.py`) | Every generated action still works, just stays local-only |
| Trigger.dev | Background execution of `/detect` and `/generate` (`app/services/trigger_client.py` + repo-root `src/trigger/`) | Same logic runs directly in-process instead |
| Exa | Citation crawl, web search, company lookup, news monitors (`/news/watch`, `/webhooks/exa`) | Research cards and news desk stay empty; pipeline still completes |
| Google / Dropbox / Microsoft | OAuth connectors (`/integrations/oauth/…`) | Cards show "not configured"; exports stay local / Ambiguous-only |
| Gemini (Vertex) | OAuth via same Google client (`gemini_oauth`) | Use key-based Gemini or skip |
| Intron Sahara | Code-switch ASR + legal refine (`transcription.py::IntronVoiceProvider`) | Default stays OpenRouter Whisper; multilingual Stop skips Sahara refine |

See `trigger/README.md` (and the repo-root Trigger worker) for deploying
Trigger.dev tasks — they need a **publicly reachable** `BACKEND_INTERNAL_URL`,
not `localhost`.

## Omi Miniapp (Settings → Connectors)

Lawyers install a private HakiScribe integration in the Omi app once. Omi then
POSTs live transcripts and finished memories to the public webhook with `uid`
(and Omi’s own conversation id). HakiScribe maps that user to an open desk
session — no pasting a per-session webhook URL.

1. Deploy the backend with a public `BACKEND_INTERNAL_URL` (the Render service URL).
2. In Omi: Explore → Create App → External integration. Enable triggers for
   **Real-time transcript** and **Memory creation** pointing at the same webhook
   when the store allows it; otherwise use a second private app or Developer Mode
   dual webhook for memory.
3. Copy Auth URL, Setup-completed URL, and Webhook URL from
   **Settings → Connectors → Omi** (or from `GET /health` → `omi_miniapp`):
   - Webhook: `{BACKEND}/webhooks/omi` (includes `?token=…` when
     `OMI_SHARED_SECRET` is configured — copy the full URL)
   - Auth: `{BACKEND}/integrations/omi/auth`
   - Setup completed: `{BACKEND}/integrations/omi/setup-completed`
4. Install the Miniapp → open Auth (Omi appends `?uid=…`) → speak into the
   wearable → a `source: "omi"` session appears on the desk.
5. Legacy demos still work: `POST /webhooks/omi?session_id=<HakiScribe UUID>`.
6. Unlinked uids are rejected (`403`). Disconnect on Connectors clears the link.

`GET /integrations/omi/setup-completed?uid=…` returns
`{"is_setup_completed": true|false}` per the Miniapp contract.
Set a long random `OMI_SHARED_SECRET` in production. HakiScribe then includes
it as a token in the generated webhook URL, which is required for every Omi
delivery; this is necessary because Omi integration webhooks do not accept
custom request headers. Legacy clients may alternatively send it as
`x-omi-secret`.

## Intron Sahara (code-switch / legal refine)

`IntronVoiceProvider` in `app/services/transcription.py` is implemented against
Sahara sync + status polling. Use it in either of two ways:

1. **Workspace key** — set `INTRON_API_KEY` (or link Intron under
   **Settings → Connectors**). Multilingual / `code-switch` sessions call
   Sahara legal court-hearing mode on Stop to refine the transcript.
2. **Primary ASR** — set `ASR_PROVIDER=intron` so live chunks also go through
   Sahara (higher latency; default product path remains OpenRouter Whisper).

Challenge packet, responsible-AI notes, and demo script:
[`../submission/README.md`](../submission/README.md). Benchmark harness:
[`benchmarking/README.md`](./benchmarking/README.md).

## What's still demo-grade (not production)

- `app/services/storage.py` — in-memory + local JSON by default; set
  `DATABASE_URL` for Postgres. Optional `S3_BUCKET` archives drafted
  documents. Supabase can host Postgres via `DATABASE_URL` but is not the
  default store or auth layer.
- `app/integrations/ambiguous_client.create_contact` — best-effort route
  (`/api/crm/contacts`); confirm the exact path against Ambiguous's live API
  reference.
- `app/routers/omi_webhook.py` — Miniapp uid + legacy UUID pairing are wired;
  confirm payload field names against Omi’s latest docs if a shape drifts.
- `app/services/storage.py::find_matter_by_client` — simple substring match;
  fine for a demo, not production matching.
- Auth is shared-workspace only — no per-lawyer session isolation yet.

See [`../SPEC.md`](../SPEC.md) for the full architecture and API contract —
written to be agent-agnostic.
