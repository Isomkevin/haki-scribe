# HakiScribe architecture

High-level map of what runs today. For the full API contract and data model, see [SPEC.md](./SPEC.md). For local setup, see [SETUP.md](./SETUP.md).

## Status legend

| Label | Meaning |
| --- | --- |
| **Implemented** | Wired in this repository and usable when configured |
| **Optional / degrades** | Works without the key; integration no-ops or falls back |
| **Planned / experimental** | Documented for production path; not the default demo mode |

---

## System overview

```
Browser (TanStack Start)          Omi wearable
  mic / UI / Action Tray            transcript webhook
           │                              │
           │  HTTP + WebSocket            │
           ▼                              ▼
              FastAPI (hakiscribe-backend)
         sessions · ASR · speakers · redaction · flags
         auth · connectors · matters · research hooks
                          │
              privilege filter (redacted lines never leave)
                          │
           Trigger.dev (src/trigger/) or in-process fallback
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     Detect (tray proposals)   Generate (selected artifacts)
     + optional research       Draft / calendar / matter / CRM /
                               time / note → Ambiguous / OAuth exports
```

**Frontend hosts:** Lovable (Cloudflare / nitro `cloudflare-module`) and optionally Vercel (nitro Build Output API). Same source; see [DEPLOYMENT.md](./DEPLOYMENT.md).

**API host:** Render Blueprint (`render.yaml`) → `hakiscribe-backend` on `0.0.0.0:$PORT`.

---

## Frontend (`src/`)

| Area | Role |
| --- | --- |
| `src/routes/` | File-based TanStack Router pages (see [src/routes/README.md](../src/routes/README.md)) |
| `src/components/hakiscribe/` | Product UI: landing, session workbench, tray, settings, connectors |
| `src/components/ui/` | Shared primitives (shadcn-style) |
| `src/lib/` | API client (`hakiscribe.ts`), auth helpers, research server functions, demo mode |
| `src/trigger/` | Trigger.dev tasks: `detect-actions`, `generate-actions`, `research-actions` |
| `src/server.ts` | TanStack Start / nitro server entry (preserve for dual deploy) |

### Routing (implemented)

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | Public | Landing only — no client work |
| `/login` | Public | Workspace sign-in |
| `/about`, `/privacy`, `/contact`, `/omi` | Public | Trust / Omi guide pages |
| `/new` | Private | Start session + library |
| `/sessions/$sessionId` | Private | Record → speakers → privilege → Action Tray |
| `/sessions/$sessionId/chat/...` | Private | Multi-thread session chat |
| `/tracker`, `/contacts`, `/research`, `/settings` | Private | Matter tracker, CRM-ish contacts, Exa research, settings |
| `/connectors` | Private | Redirect → `/settings?section=connectors` |

Private routes use `RequireAuth`. Default auth is a browser-held bearer token from `POST /auth/login`. Optional production auth (`VITE_PRODUCTION_AUTH` + `HAKISCRIBE_PRODUCTION_AUTH`) uses cookie sessions against Supabase — see [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md).

---

## Backend (`hakiscribe-backend/`)

FastAPI app in `app/main.py`. Routers under `app/routers/`:

| Prefix / area | Responsibility |
| --- | --- |
| `/auth` | Demo/workspace login (`HAKISCRIBE_USERS`), demo credentials |
| `/auth/production`, `/organisations`, `/production/*` | **Experimental** tenancy / Supabase production path |
| `/sessions` | CRUD, finalize, speakers, segments, flags, detect, generate, chat |
| `/sessions/{id}/stream` | WebSocket mic audio → live captions |
| `/webhooks/omi`, `/integrations/omi/*` | Omi Miniapp + legacy session webhook |
| `/matters`, `/contacts` | Matter registry and contacts |
| `/integrations` | Connector keys, OAuth start/callback, health tests |
| `/news`, `/webhooks/exa` | Exa news monitors |
| `/demo` | Judge demos including live Nemotron path |
| `/internal` | Trigger.dev worker callbacks (secret-gated) |
| `/health`, `/usage`, `/models` | Ops and model discovery |

Services live in `app/services/` (transcription, detection, generation, storage, Nebius, Tavily, OAuth). External clients live in `app/integrations/` (Ambiguous, Exa, HakiChain, LLM).

### Storage (implemented)

- **Default:** in-memory + local JSON (`app/services/storage.py`) — ephemeral on Render free tier.
- **Optional:** `DATABASE_URL` → Postgres.
- **Optional:** `S3_BUCKET` → draft document archive.

### Auth (implemented vs planned)

| Mode | Status |
| --- | --- |
| Shared workspace + `HAKISCRIBE_USERS` + bearer token | **Implemented** (default demo) |
| Temporary demo account (`DEMO_LOGIN_ENABLED`) | **Implemented** |
| Per-lawyer vaults / firm RLS tenancy | **Planned** — see production routers + [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md) |

---

## AI & RAG pipeline (implemented)

1. **ASR** — provider abstraction in `transcription.py`: OpenRouter Whisper (default), OpenAI, Groq, Intron Sahara, optional NVIDIA NIM.
2. **Privilege gate** — redacted segments stripped in code before any detect/generate/research LLM call.
3. **Detect** — Action Tray proposals (Nemotron Super on Nebius when connected; else OpenRouter / configured LLM). Citations must reference real non-privileged lines.
4. **Generate** — type-specific artifacts (Nemotron Ultra for drafts when Nebius is active).
5. **Research** — Tavily over Kenyan legal domains (labelled external authorities, not evidence) and/or Exa company/citation/news. Frontend `/research` may also use Exa via TanStack server functions (`EXA_API_KEY`).

Nebius Token Factory is the preferred AI compute when a key is connected (Connectors → AI Compute). There is **no silent fallback** from Nebius to OpenRouter when Nebius is the selected provider.

Trigger.dev runs detect/generate/research durably when `TRIGGER_SECRET_KEY` is set; otherwise the same Python logic runs in-process.

---

## Blockchain / HakiChain

HakiScribe is the listening instrument of [HakiChain](https://hakichain.com). Document verification on-chain is **not** the core of this repo’s demo path.

| Integration | Status |
| --- | --- |
| HakiChain connector (`HAKICHAIN_API_BASE`, lawyer `hkc_…` token) | **Implemented** as optional workspace filing |
| Full on-chain document attestation / NFT flows | **Out of scope** here — belongs to HakiChain product surfaces |

---

## Deployment topology

```
┌─────────────────────┐     ┌─────────────────────┐
│ Lovable frontend    │     │ Vercel frontend     │  (optional second host)
│ hakiscribe.lovable… │     │ (same build source) │
└──────────┬──────────┘     └──────────┬──────────┘
           │  VITE_API_BASE_URL        │
           └────────────┬──────────────┘
                        ▼
           ┌────────────────────────┐
           │ Render FastAPI         │
           │ hakiscribe-backend…    │
           └────────────┬───────────┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
     Trigger.dev   Nebius/TF     OAuth providers
     (optional)    Tavily/Exa    Ambiguous / cloud drives
```

Connector OAuth callbacks stay on the Render backend (`/integrations/oauth/{provider}/callback`). Details: [CONNECTOR_OAUTH_SETUP.md](./CONNECTOR_OAUTH_SETUP.md), [DEPLOYMENT.md](./DEPLOYMENT.md).

---

## Related docs

- [SPEC.md](./SPEC.md) — canonical API + data model
- [SETUP.md](./SETUP.md) — run locally
- [../hakiscribe-backend/README.md](../hakiscribe-backend/README.md) — API runbook
- [PRODUCT_GUIDE.md](./PRODUCT_GUIDE.md) — product behaviour
