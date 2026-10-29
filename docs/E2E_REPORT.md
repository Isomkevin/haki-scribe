# Nebius × NVIDIA — E2E report

Date: 2026-10-29  
Environment: local Windows workspace for HakiScribe.

## Secrets available in this environment

| Secret | Status |
| --- | --- |
| `NEBIUS_API_KEY` | **unset** |
| `TAVILY_API_KEY` | **unset** |
| `OPENROUTER_API_KEY` | not checked for this report |

Live Token Factory / Tavily calls were **not** run. Do not treat any demo as live until you run the commands below with real keys.

## Verified by running (no API key required)

```text
cd hakiscribe-backend
python -m unittest tests.test_tray_logic tests.test_nebius_privilege -v
```

Result: **7 passed** (OK), including:

- Privileged lines absent from `build_transcript_block`
- Actions citing only privileged/nonexistent quotes dropped
- Confidence clamp + duplicate handling
- `extract_json` with `<think>` blocks and fences
- **Privilege interception** (`ZEBRA-PRIVILEGED-7731` absent from mocked Nebius request body and `ai_runs`)
- Tier resolution failure message lists available Nemotron models
- `is_connected()` false when only `base_url` is set

## Live chain — commands for you

```bash
cd hakiscribe-backend
# Windows PowerShell
$env:NEBIUS_API_KEY="…"
$env:TAVILY_API_KEY="…"   # optional, for research step
python scripts/smoke_nebius.py
```

Expected steps in the smoke script:

1. `GET /v1/models` → Nemotron models + resolved Ultra/Super  
2. Detection (Super) on Kiswahili/English intake with privileged marker → marker absent  
3. Draft (Ultra) → Markdown / letter with `[CONFIRM: …]` style placeholders when facts missing  
4. Research (Tavily + Super) when `TAVILY_API_KEY` set  
5. `ai_runs` rows with no transcript text  

Also:

```bash
curl -s -H "Authorization: Bearer $NEBIUS_API_KEY" https://api.tokenfactory.nebius.com/v1/models
```

Apply production migration (if using Supabase Postgres):

```text
hakiscribe-backend/migrations/002_provider_settings_ai_runs.sql
```

Redeploy backend (Render) then frontend (Lovable/Vercel). Confirm Connectors → Test connection lists Nemotron tiers; Backend → Run diagnostics all green.

## Manual UI walk-through (no Playwright in repo)

1. Start backend + `npm run dev`.  
2. Settings → Connectors → NVIDIA Nemotron · Nebius Token Factory → paste key → Test connection.  
3. Confirm AI Compute panel shows Connected + tiers.  
4. New session → record or load demo → lock one line as privileged → Stop.  
5. Tray appears pre-checked; banner shows “N privileged lines excluded from AI”.  
6. Click a Source chip → Record tab highlights the line.  
7. Untick one action → Generate selected → edit draft; footer shows model id.  
8. Research action → “External authorities (not evidence)”.  
9. Settings → Backend → Run diagnostics → all green when keys set.  
10. Disconnect Nebius → demo/heuristic path still works without key.

## Failure drills (expected behaviour)

| Failure | Expected |
| --- | --- |
| Wrong API key | Clear error toast / connector check fail; no silent OpenRouter switch |
| Bad base URL | Error from GET `/models` / complete |
| Model not found | Error listing available Nemotron models |
| Invalid JSON from model | Repair pass; still no silent provider switch |
| 429 | One retry with backoff, then surfaced error |

## Lint / build

- `npm run lint` reports a large number of pre-existing `prettier/prettier` CRLF (`Delete ␍`) issues across the repo (15k+); not introduced by the Nebius finish. Prefer `npm run build` as the ship check.
- Unit tests: `python -m unittest tests.test_tray_logic tests.test_nebius_privilege -v` → **7 passed**.

## Known issues

- Live Nebius/Tavily chain not captured in this file (keys unset here).  
- Frontend has no `typecheck`/`test` npm scripts.  
- Reference Edge Function tree remains gitignored under `reference/` (not shipped).
