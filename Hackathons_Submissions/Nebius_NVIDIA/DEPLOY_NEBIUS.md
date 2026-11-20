# Deploy Nebius Token Factory on Render

Service: **hakiscribe-backend** (`srv-daikp8uk1f9s738k51lg`)  
URL: https://hakiscribe-backend.onrender.com  
Dashboard: https://dashboard.render.com/web/srv-daikp8uk1f9s738k51lg  
Auto-deploy: on push to `main` when `hakiscribe-backend/**` or `render.yaml` changes.

## Status (2026-10-29)

| Check | Result |
| --- | --- |
| Hosted `/health` | **PASS** — `status: ok`, mode `demo` |
| `NEBIUS_API_KEY` on Render | **UNVERIFIED** — must set in dashboard (never commit) |
| `TAVILY_API_KEY` on Render | **UNVERIFIED** |
| Provider-precedence + live demo code on `main` | **FAIL until you commit + push** — changes are local |

`LLM_PROVIDER=openrouter` may stay in the Blueprint. After the precedence fix, a connected Nebius key overrides it at runtime.

## What you must do (manual)

1. **Set secrets** in Render → hakiscribe-backend → Environment:
   - `NEBIUS_API_KEY` = your Token Factory key
   - `TAVILY_API_KEY` = your Tavily key (for research + Best Use of Tavily)
   - Optional: `NEMOTRON_ULTRA_MODEL`, `NEMOTRON_SUPER_MODEL`, `NEMOTRON_NANO_MODEL` if discovery fails
2. **Commit and push** the local Nebius work to `main` (or ask the agent to commit when you approve). Render will auto-deploy.
3. Wait for deploy green, then:
   ```bash
   curl -s https://hakiscribe-backend.onrender.com/health
   ```
4. Open the frontend → Settings → Connectors → Test connection for Nebius and Tavily.
5. `/new` → **Run live Nemotron demo** → Detect → Generate letter → Research.

## Agent cannot complete without

- Your Nebius and Tavily API key values (to set env vars or run smoke).
- Explicit approval to **git commit** and **git push** (auto-deploy needs the push).

Do not paste keys into chat if you prefer the Render UI — set them only in the dashboard.
