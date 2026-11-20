# HakiScribe documentation

Index of project documentation. Start with the [root README](../README.md) for product context and quick start, then use this map for deeper topics.

## Essential

| Doc | Purpose |
| --- | --- |
| [SETUP.md](./SETUP.md) | Local development, env vars, scripts, troubleshooting |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design: frontend, API, AI pipeline, storage, deploy |
| [SPEC.md](./SPEC.md) | Detailed build spec, data model, and API contract |
| [PRODUCT_GUIDE.md](./PRODUCT_GUIDE.md) | Product capabilities, safeguards, and journey |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Lovable + Vercel dual frontend deploy; Render API |

## Operations & security

| Doc | Purpose |
| --- | --- |
| [CONNECTOR_OAUTH_SETUP.md](./CONNECTOR_OAUTH_SETUP.md) | Google / Dropbox / Microsoft / Gemini OAuth on Render |
| [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md) | Tenancy, identity, MFA, and production migration plan |
| [nvidia-nim.md](./nvidia-nim.md) | Optional self-hosted NVIDIA NIM ASR/LLM |
| [DEPLOY_NEBIUS.md](./DEPLOY_NEBIUS.md) | Nebius Token Factory secrets and Render checklist |

## Backend & frontend module docs

| Doc | Purpose |
| --- | --- |
| [../hakiscribe-backend/README.md](../hakiscribe-backend/README.md) | FastAPI runbook, auth, Omi, demo HTTP path |
| [../src/routes/README.md](../src/routes/README.md) | TanStack file-based routing conventions |
| [../hakiscribe-backend/benchmarking/README.md](../hakiscribe-backend/benchmarking/README.md) | ASR benchmark harness |
| [../hakiscribe-backend/migrations/README.md](../hakiscribe-backend/migrations/README.md) | Postgres / tenancy migrations |
| [../hakiscribe-backend/trigger/README.md](../hakiscribe-backend/trigger/README.md) | Legacy Trigger notes (canonical tasks: `src/trigger/`) |

## Roadmap & submissions

| Doc | Purpose |
| --- | --- |
| [roadmap.md](./roadmap.md) | Done checklist + remaining external setup |
| [NEBIUS_SUBMISSION.md](./NEBIUS_SUBMISSION.md) | Nebius × NVIDIA hackathon packet |
| [DEMO_SCRIPT_NEBIUS.md](./DEMO_SCRIPT_NEBIUS.md) | Under-3-minute demo / video script |
| [E2E_REPORT.md](./E2E_REPORT.md) | End-to-end Nebius / Nemotron notes |
| [FEEDBACK.md](./FEEDBACK.md) | Judge / reviewer feedback log |
| [SUBMISSION_READINESS.md](./SUBMISSION_READINESS.md) | Nebius submission readiness checklist |
| [SUBMISSION.md](./SUBMISSION.md) | AI Tinkerers Nairobi packet (legacy stack notes) |
| [../Hackathon_Submission/](../Hackathon_Submission/README.md) | Packaged hackathon submission folders |
| [../Sahara_CodeSwitch_Africa_Challenge_submission/](../Sahara_CodeSwitch_Africa_Challenge_submission/README.md) | Sahara CodeSwitch Africa packet |
| [../GOMYCODE_x_NVIDIA_Hackathon_Submission/](../GOMYCODE_x_NVIDIA_Hackathon_Submission/README.md) | GOMYCODE Come Build with AI packet |

## Conventions

- Prefer placeholders (`your-key-here`, `https://example.com`) in examples — never commit real secrets.
- Secrets belong in `.env.local` (local) or platform secret stores (Render, Lovable Cloud Secrets, Vercel, Trigger.dev). Do **not** put secrets in the committed root `.env` (Lovable publishes it).
- Distinguish **implemented** behaviour from **planned** production work (see [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md)).
