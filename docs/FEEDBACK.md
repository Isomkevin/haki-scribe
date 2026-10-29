# Feedback — Nebius Token Factory, Nemotron, Tavily

Placeholders for **real** observations from live runs. Do not invent measurements.

## Nebius Token Factory

| Topic | Observation |
| --- | --- |
| Latency (`GET /models`) | _TBD after live smoke_ |
| Latency (chat completions, Super) | _TBD_ |
| Latency (chat completions, Ultra) | _TBD_ |
| Auth / key UX | _TBD_ |
| Base URL quirks | _TBD_ |

## NVIDIA Nemotron Super

| Topic | Observation |
| --- | --- |
| JSON reliability (`response_format` / repair) | _TBD_ |
| Action Tray quality (Kenyan legal rooms) | _TBD_ |
| Code-switching (English / Kiswahili / Sheng) | _TBD_ |
| Citation honesty (`source_quote`) | _TBD_ |

## NVIDIA Nemotron Ultra

| Topic | Observation |
| --- | --- |
| Draft quality / Kenyan form | _TBD_ |
| `[CONFIRM: …]` placeholder behaviour | _TBD_ |
| Hallucinated statutes/cases (should be none unless on record) | _TBD_ |

## Tavily

| Topic | Observation |
| --- | --- |
| Kenyan domain coverage (`kenyalaw.org`, etc.) | _TBD_ |
| Latency | _TBD_ |
| Usefulness as “external authorities (not evidence)” | _TBD_ |

## How to fill this in

1. Run `python hakiscribe-backend/scripts/smoke_nebius.py` with live keys.  
2. Record p50/p95 latencies and paste short notes above.  
3. Attach links to `docs/E2E_REPORT.md` captures if useful.
