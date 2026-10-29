# Submission readiness — Nebius × NVIDIA (2026-10-29)

Labels: **PASS** / **FAIL** / **UNVERIFIED**. Nothing is PASS without evidence.

| Item | Status | Evidence |
| --- | --- | --- |
| Track selected: Best Apps and Agents | **PASS** | Product is a usable legal app/agent; packet in `docs/NEBIUS_SUBMISSION.md` |
| Runtime Nebius Token Factory call | **UNVERIFIED** | Client + smoke script exist; `NEBIUS_API_KEY` unset in this workspace |
| NVIDIA open model (Nemotron) | **UNVERIFIED** | Code path uses discovered Nemotron tiers; live model id not captured |
| Tavily runtime call (bonus) | **UNVERIFIED** | `tavily.py` + research path; `TAVILY_API_KEY` unset |
| Working demo URL | **PASS** | https://hakiscribe.lovable.app/ + https://hakiscribe-backend.onrender.com/health (`status: ok`) |
| Public repo + MIT license | **PASS** | `LICENSE` MIT; GitHub `Isomkevin/haki-scribe` (confirm About shows license) |
| README setup + Nebius disclosure | **PASS** | README updated; `docs/NEBIUS_SUBMISSION.md` |
| Significant-update explanation | **PASS** | README + NEBIUS_SUBMISSION |
| Demo video ≤3 min YouTube | **FAIL** | Script ready in `docs/DEMO_SCRIPT_NEBIUS.md`; video not recorded |
| Feedback submitted | **FAIL** | Draft in `docs/FEEDBACK.md`; needs live observations then Devpost paste |
| Provider precedence fix | **PASS** | Unit tests: connected Nebius overrides `LLM_PROVIDER=openrouter` |
| Live short demo (not padded catalog) | **PASS** (code) | `POST /demo/live-nemotron` + UI button; hosted deploy of this commit **UNVERIFIED** until push |
| Hosted secrets NEBIUS/TAVILY | **UNVERIFIED** | See `docs/DEPLOY_NEBIUS.md` |
| No secrets in git | **PASS** | Keys not committed; examples empty |
| GDPR / production claims | **PASS** (doc hygiene) | Devpost copy avoids GDPR production claim |

## Your remaining manual steps before Devpost submit

1. Set `NEBIUS_API_KEY` (+ `TAVILY_API_KEY`) locally → `python scripts/smoke_nebius.py` → fill `docs/FEEDBACK.md`.  
2. Approve git **commit** + **push** of this work → Render auto-deploys.  
3. Set the same keys in Render dashboard → verify Connectors Test connection.  
4. Record the video from `docs/DEMO_SCRIPT_NEBIUS.md`.  
5. Submit on Devpost with track, URLs, feedback, significant-update text.
