# Feedback — Nebius Token Factory, Nemotron, Tavily

Fill only from a live `smoke_nebius.py` run or a verified UI journey. Do not invent measurements.

**Status (2026-10-29):** LIVE CHAIN **UNVERIFIED** in this workspace — `NEBIUS_API_KEY` and `TAVILY_API_KEY` were unset when the submission prep ran. Re-run the smoke script after setting keys, then replace every `_TBD_` below.

## How to run (required before Devpost submit)

```powershell
cd hakiscribe-backend
$env:NEBIUS_API_KEY="…"   # Token Factory key — never commit
$env:TAVILY_API_KEY="…"   # optional but needed for Best Use of Tavily evidence
python scripts/smoke_nebius.py
```

Expected: models list with Nemotron Ultra/Super/Nano; Super detection JSON; Ultra draft; privileged marker `ZEBRA-PRIVILEGED-7731` absent from outbound bodies; Tavily hits when key set.

## Nebius Token Factory

| Topic | Observation |
| --- | --- |
| Latency (`GET /models`) | _TBD after live smoke_ |
| Latency (chat completions, Super) | _TBD_ |
| Latency (chat completions, Ultra) | _TBD_ |
| Auth / key UX | Connector + env path implemented; live auth **UNVERIFIED** |
| Base URL quirks | Default `https://api.tokenfactory.nebius.com/v1` — live **UNVERIFIED** |

## NVIDIA Nemotron Super

| Topic | Observation |
| --- | --- |
| JSON reliability (`response_format` / repair) | Unit-tested extract path; live **UNVERIFIED** |
| Action Tray quality (Kenyan legal rooms) | Live **UNVERIFIED** |
| Code-switching (English / Kiswahili / Sheng) | Live **UNVERIFIED** |
| Citation honesty (`source_quote`) | Live **UNVERIFIED** |

## NVIDIA Nemotron Ultra

| Topic | Observation |
| --- | --- |
| Draft quality / Kenyan form | Live **UNVERIFIED** |
| `[CONFIRM: …]` placeholder behaviour | Live **UNVERIFIED** |
| Hallucinated statutes/cases (should be none unless on record) | Live **UNVERIFIED** |

## Tavily

| Topic | Observation |
| --- | --- |
| Kenyan domain coverage (`kenyalaw.org`, etc.) | Live **UNVERIFIED** |
| Latency | _TBD_ |
| Usefulness as “External authorities (not evidence)” | Live **UNVERIFIED** |

## Devpost feedback draft (paste after live run)

Replace bracketed notes with real observations:

> Token Factory’s OpenAI-compatible chat API made it straightforward to swap HakiScribe’s Action Tray (Nemotron Super) and drafting (Ultra) without rewriting the FastAPI pipeline. Live model discovery via `GET /models` avoided hardcoding ids. [Note: latency / JSON reliability / anything that failed.] Privilege exclusion is enforced before the request leaves the server — we verified the privileged marker never appears in the outbound body [cite smoke output]. Tavily advanced search over Kenyan legal domains supplies research cards labelled as external authorities, not transcript evidence [cite hit count / sample URL]. Wish list: [honest product feedback after the run].
