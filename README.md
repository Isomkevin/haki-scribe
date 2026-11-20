# HakiScribe

**The conversation is the work. The transcript is only the witness.**

HakiScribe is a legal work agent for client meetings, chambers, and court. It listens from a phone, laptop, or [Omi](https://omi.me) wearable, then proposes a tray of concrete artifacts — draft letters, hearing dates, matters, billable time, private notes — each grounded in what was actually said. Privileged lines stay redacted before any model call. The professional selects, edits, and owns every output.

Built as the listening instrument of [HakiChain](https://hakichain.com). Live app: [hakiscribe.lovable.app](https://hakiscribe.lovable.app/). Demo walkthrough: [YouTube](https://youtu.be/FjsZqMBsCfs).

| Resource | Link |
| --- | --- |
| Documentation index | [docs/README.md](./docs/README.md) |
| Local setup | [docs/SETUP.md](./docs/SETUP.md) |
| Architecture | [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| API / data contract | [docs/SPEC.md](./docs/SPEC.md) |
| Backend runbook | [hakiscribe-backend/README.md](./hakiscribe-backend/README.md) |
| Deploy (Lovable + Vercel) | [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) |

---

## What is implemented

| Capability | Notes |
| --- | --- |
| Mic capture + live captions | Browser MediaRecorder → WebSocket `/sessions/{id}/stream` |
| Omi Miniapp / webhook | Wearable transcript ingestion + uid pairing |
| Flag / speakers / privilege | No-look flags; name speakers; redact before AI |
| Action Tray | Detect → select → generate (draft, calendar+.ics, matter, CRM, time, note) |
| AI compute | Nebius Token Factory + NVIDIA Nemotron when connected; OpenRouter / other providers selectable |
| Research | Tavily (external authorities) + Exa citation/news paths |
| Connectors | Verified LLM keys; Google Drive/Calendar, Dropbox, OneDrive OAuth |
| Delivery | Ambiguous AI Docs/Calendar/CRM/Chat when keyed; else local-only |
| Auth | Shared workspace accounts + optional demo login (not firm tenancy yet) |
| Deploy | Frontend: Lovable (+ optional Vercel). API: Render Blueprint |

**Not production-ready for real client/court data** without the tenancy and identity work in [docs/PRODUCTION_READINESS.md](./docs/PRODUCTION_READINESS.md). All signed-in users currently share one workspace.

Product detail: [docs/PRODUCT_GUIDE.md](./docs/PRODUCT_GUIDE.md).

---

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TanStack Start, Vite, Tailwind CSS |
| Backend | FastAPI, WebSockets |
| Storage | Memory + local JSON by default; optional `DATABASE_URL` (Postgres), optional S3 drafts |
| Speech | OpenRouter Whisper default; OpenAI / Groq / Intron Sahara / NVIDIA NIM optional |
| Agents | Nebius Nemotron (Super detect/research, Ultra drafts) or OpenRouter/Claude/GPT |
| Jobs | Trigger.dev at `src/trigger/` with in-process fallback |
| Auth | Server accounts + signed browser token (`POST /auth/login`) |

---

## Repository structure

```
HakiScribe/
├── src/                    # Frontend (routes, components, lib, Trigger tasks)
├── hakiscribe-backend/     # FastAPI API, services, integrations, tests
├── docs/                   # Architecture, setup, deploy, submissions
├── public/                 # Static assets / PWA
├── Hackathon_Submission/   # Packaged Nebius × NVIDIA materials
├── Sahara_CodeSwitch_…/    # Sahara challenge packet
├── GOMYCODE_x_NVIDIA_…/    # GOMYCODE submission packet
├── reference/              # Reference / experimental material (not the main app)
├── render.yaml             # Render Blueprint for the API
└── package.json            # Frontend scripts
```

---

## Quick start

Prerequisites: **Node.js ≥ 20.19**, **Python 3.11+**, npm or bun. Full guide: [docs/SETUP.md](./docs/SETUP.md).

```bash
# Backend
cd hakiscribe-backend
pip install -r requirements.txt
cp .env.example .env.local    # set OPENROUTER_API_KEY (and optional NEBIUS_API_KEY / TAVILY_API_KEY)
uvicorn app.main:app --reload --port 8000

# Frontend (repo root)
cp .env.example .env.local    # VITE_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev

# Optional durable jobs
npm run trigger:dev
```

### Environment (safe examples)

| Location | Examples (placeholders only) |
| --- | --- |
| Root `.env.local` | `VITE_API_BASE_URL=http://127.0.0.1:8000` |
| Backend `.env.local` | `OPENROUTER_API_KEY=…`, `NEBIUS_API_KEY=…`, `AUTH_SECRET=…`, `HAKISCRIBE_USERS=you@example.com:password\|Name` |

Never put secrets in the committed root `.env` (Lovable publishes it). Templates: [`.env.example`](./.env.example), [`hakiscribe-backend/.env.example`](./hakiscribe-backend/.env.example).

### Test & build

```bash
npm test
npm run lint
npm run build
```

---

## App routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | Public | Landing |
| `/login` | Public | Sign-in |
| `/new` | Private | Start session + library |
| `/sessions/$sessionId` | Private | Capture → Action Tray |
| `/tracker` / `/contacts` / `/research` / `/settings` | Private | Matters, contacts, research, connectors |

---

## How the pipeline works

```
Mic / Omi → FastAPI (session, ASR, speakers, redaction, flags)
         → privilege filter
         → Detect (tray) → user selects → Generate (artifacts)
         → Ambiguous / Drive / Calendar / local results
```

Two LLM passes after transcription: **detection** proposes source-grounded work; **generation** runs only for selected cards. Redacted lines never leave the privilege filter.

More detail: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## Contribution

1. Read [docs/SETUP.md](./docs/SETUP.md) and [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
2. Keep frontend and backend behaviour aligned with [docs/SPEC.md](./docs/SPEC.md).
3. Prefer `.env.local` for secrets; do not commit credentials.
4. Match existing TypeScript / Python style; run `npm test` and `npm run lint` before opening a PR.
5. This repo is connected to Lovable — avoid force-pushing or rewriting published history on the connected branch (see [AGENTS.md](./AGENTS.md)).

Questions about product intent: [docs/PRODUCT_GUIDE.md](./docs/PRODUCT_GUIDE.md). Roadmap / remaining external setup: [docs/roadmap.md](./docs/roadmap.md).

---

## Team

**Kevin Isom** — Lead; architecture, FastAPI pipeline, integrations, deploy.  
**Mercy Wairimu** — Product and legal workflow; mobile-first experience and Kenyan practice (English / Kiswahili / code-switch).

---

## Hackathon & challenge packets

| Packet | Location |
| --- | --- |
| Nebius × NVIDIA | [docs/NEBIUS_SUBMISSION.md](./docs/NEBIUS_SUBMISSION.md), [Hackathon_Submission/](./Hackathon_Submission/README.md) |
| Sahara CodeSwitch Africa | [Sahara_CodeSwitch_Africa_Challenge_submission/](./Sahara_CodeSwitch_Africa_Challenge_submission/README.md) |
| GOMYCODE | [GOMYCODE_x_NVIDIA_Hackathon_Submission/](./GOMYCODE_x_NVIDIA_Hackathon_Submission/README.md) |
| AI Tinkerers Nairobi (legacy) | [docs/SUBMISSION.md](./docs/SUBMISSION.md) |

---

**Leave the room with the work already begun.**
