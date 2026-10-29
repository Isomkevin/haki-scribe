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
python -m unittest tests.test_tray_logic tests.test_nebius_privilege tests.test_live_nemotron_demo -v
```

Result: **12+ passed** (OK), including:

- Privileged lines absent from `build_transcript_block`
- Actions citing only privileged/nonexistent quotes dropped
- Confidence clamp + duplicate handling
- `extract_json` with `<think>` blocks and fences
- **Privilege interception** (`ZEBRA-PRIVILEGED-7731` absent from mocked Nebius request body and `ai_runs`)
- Tier resolution failure message lists available Nemotron models
- `is_connected()` false when only `base_url` is set
- **`select_provider`**: connected Nebius overrides `LLM_PROVIDER=openrouter`; `nvidia_nim` env still wins; disconnected keeps openrouter
- Live Nemotron demo spec is short (12–25 lines), privilege-indexed, `generate=False`, no working-session padding

Smoke without key:

```text
python scripts/smoke_nebius.py
→ SKIP: NEBIUS_API_KEY is not set (exit 2)
```

## Live chain — commands for you (BLOCKER for eligibility)

```powershell
cd hakiscribe-backend
$env:NEBIUS_API_KEY="…"
$env:TAVILY_API_KEY="…"   # optional, for research step / Tavily bonus evidence
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

## Hosted backend (observed 2026-10-29)

`GET https://hakiscribe-backend.onrender.com/health` → `status: ok`, `mode: demo`.  
Integrations report OpenRouter / Trigger / Exa / Ambiguous present. Nebius is **not** confirmed connected on that instance until `NEBIUS_API_KEY` is set in the Render dashboard and the provider-precedence fix is deployed.

## Manual UI walk-through (after keys + deploy)

1. Start backend + `npm run dev` (or use hosted frontend).  
2. Settings → Connectors → NVIDIA Nemotron · Nebius Token Factory → paste key → Test connection.  
3. Confirm AI Compute panel shows Connected + tiers.  
4. `/new` → **Run live Nemotron demo** (not the saved sample).  
5. Confirm speakers → privilege (tax line already struck) → Detect.  
6. Tray appears; banner / footer shows Nemotron Super. Click Source chip.  
7. Generate demand letter → Ultra footer with model id.  
8. Research action → “External authorities (not evidence)” with Tavily URLs.  
9. Settings → Backend → Run diagnostics → all green when keys set.  
10. Disconnect Nebius → demo/heuristic path still works without key; with Nebius connected, failures must surface (no silent OpenRouter switch).

## Failure drills (expected behaviour)

| Failure | Expected |
| --- | --- |
| Wrong API key | Clear error toast / connector check fail; no silent OpenRouter switch |
| Bad base URL | Error from GET `/models` / complete |
| Model not found | Error listing available Nemotron models |
| Invalid JSON from model | Repair pass; still no silent provider switch |
| 429 | One retry with backoff, then surfaced error |

## Lint / build

- `npm run lint` reports a large number of pre-existing `prettier/prettier` CRLF (`Delete ␍`) issues across the repo; not introduced by the Nebius finish. Prefer `npm run build` as the ship check.
- Unit tests above: **PASS**. Live smoke: **UNVERIFIED** (keys unset).

## Known issues / submission blockers remaining

- Live Nebius/Tavily chain not captured (keys unset here).  
- Hosted Render must receive `NEBIUS_API_KEY` + `TAVILY_API_KEY` via dashboard and a deploy of the precedence + live-demo code.  
- Frontend has no `typecheck`/`test` npm scripts.  
- Reference Edge Function tree remains gitignored under `reference/` (not shipped).
