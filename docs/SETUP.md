# Developer setup

Verified against `package.json`, `hakiscribe-backend/requirements.txt`, and the committed `.env.example` files. For dual-host deploy, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Prerequisites

| Tool | Notes |
| --- | --- |
| Node.js ≥ 20.19 | Declared in root `package.json` → `engines` |
| npm or bun | Both lockfiles are committed (`package-lock.json`, `bun.lock`) — keep them in sync |
| Python 3.11+ | Backend; see `hakiscribe-backend/.python-version` if present |
| pip | Backend dependencies |

Optional: Trigger.dev CLI (invoked via `npm run trigger:dev`), Render account for API deploy, OAuth app credentials for cloud connectors.

## Repository layout (dev-relevant)

```
HakiScribe/
├── src/                      # TanStack Start frontend + Trigger tasks
├── hakiscribe-backend/       # FastAPI API
├── docs/                     # This documentation set
├── public/                   # Static assets, PWA
├── render.yaml               # Render Blueprint for the API
├── .env.example              # Frontend / Trigger env template
└── package.json              # Frontend scripts
```

## 1. Clone and install

```bash
git clone https://github.com/Isomkevin/haki-scribe.git
cd haki-scribe

# Frontend
cp .env.example .env.local
npm install                   # or: bun install

# Backend
cd hakiscribe-backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
cd ..
```

## 2. Environment configuration

### Frontend / Trigger (repo root `.env.local`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Yes (local) | e.g. `http://127.0.0.1:8000` |
| `VITE_PRODUCTION_AUTH` | No | `true` only with backend production auth |
| `EXA_API_KEY` | No | Research page citation search (server-side) |
| `TRIGGER_SECRET_KEY` | No | Durable detect/generate/research |
| `TRIGGER_PROJECT_REF` | No | Defaults aligned with `trigger.config.ts` |
| `BACKEND_INTERNAL_URL` | For Trigger | Public API URL Trigger can reach |
| `BACKEND_INTERNAL_SECRET` | For Trigger | Shared secret for `/internal/*` |

Do **not** put secrets in the committed `.env` (Lovable publishes it). That file should only carry the public production `VITE_API_BASE_URL`.

### Backend (`hakiscribe-backend/.env.local`)

Minimum for a useful local demo:

```env
OPENROUTER_API_KEY=your-openrouter-key
AUTH_SECRET=replace-with-a-long-random-string
HAKISCRIBE_USERS=you@example.com:choose-a-password|Your Name
DEMO_LOGIN_ENABLED=true
```

Common optional keys (placeholders only):

```env
NEBIUS_API_KEY=your-nebius-token-factory-key
TAVILY_API_KEY=your-tavily-key
EXA_API_KEY=your-exa-key
AMBIGUOUS_API_KEY=your-ambiguous-key
INTRON_API_KEY=your-intron-key
TRIGGER_SECRET_KEY=tr_dev_your-key
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
BACKEND_INTERNAL_SECRET=shared-dev-secret
DATABASE_URL=               # empty = memory + JSON
LLM_PROVIDER=openrouter     # or nebius | nvidia_nim
ASR_PROVIDER=openrouter
```

Full annotated list: [`hakiscribe-backend/.env.example`](../hakiscribe-backend/.env.example). OAuth connector vars: [CONNECTOR_OAUTH_SETUP.md](./CONNECTOR_OAUTH_SETUP.md).

## 3. Run locally

Use three terminals as needed.

**Backend**

```bash
cd hakiscribe-backend
uvicorn app.main:app --reload --port 8000
```

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

**Frontend**

```bash
npm run dev
```

**Trigger.dev (optional)**

```bash
npm run trigger:dev
```

Requires `TRIGGER_SECRET_KEY` and a reachable `BACKEND_INTERNAL_URL` (localhost only works for local Trigger; cloud Trigger needs a public URL).

### Nebius smoke (optional)

```bash
cd hakiscribe-backend
python scripts/smoke_nebius.py
```

## 4. Scripts (frontend)

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite / TanStack Start dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run test` | Vitest (`vitest run`) |
| `npm run lint` | ESLint |
| `npm run format` | Prettier write |
| `npm run trigger:dev` | Trigger.dev local worker |
| `npm run trigger:deploy` | Deploy Trigger tasks |

Vercel-shaped build check (optional):

```bash
NITRO_PRESET=vercel npm run build
```

## 5. Testing

```bash
# Frontend unit tests
npm test

# Backend (from hakiscribe-backend, if pytest deps installed)
# See hakiscribe-backend/tests/ and benchmarking/README.md
```

HTTP-only demo without a microphone: follow the step list in [hakiscribe-backend/README.md](../hakiscribe-backend/README.md) (`POST /sessions` → Omi webhook → speakers → redaction → detect → generate).

## 6. Troubleshooting

| Symptom | What to check |
| --- | --- |
| Frontend cannot reach API | `VITE_API_BASE_URL` in `.env.local`; backend listening on that host/port |
| CORS / auth failures | Backend `HAKISCRIBE_ALLOWED_ORIGINS` for production auth; demo mode uses bearer tokens |
| Detect/generate fails with Nebius selected | `NEBIUS_API_KEY`; Settings → AI Compute / diagnostics; no silent OpenRouter fallback |
| Captions empty | `OPENROUTER_API_KEY` or alternate `ASR_PROVIDER` + key |
| Trigger tasks never run | Missing `TRIGGER_SECRET_KEY` → in-process fallback is expected; cloud Trigger cannot call `localhost` |
| Render cold start | Free tier sleeps after idle — first request may take longer |
| Research “not configured” | Set `EXA_API_KEY` and/or `LOVABLE_API_KEY` on the frontend host |

## 7. Security notes for developers

- Never commit API keys, OAuth secrets, or `AUTH_SECRET` / `BACKEND_INTERNAL_SECRET`.
- Prefer `.env.local` over editing committed `.env`.
- Disable `DEMO_LOGIN_ENABLED` before any real client data.
- Treat transcripts as privileged: redaction must happen before model calls (enforced in backend services).

## Next reading

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [../hakiscribe-backend/README.md](../hakiscribe-backend/README.md)
