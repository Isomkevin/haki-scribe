# Verification harnesses (1A)

Run these **before** claiming Zoom/Teams/Kiswahili/live-bot success. Live runs (1B) require real sandboxes and consented audio — do not mark verified without evidence in `09-testing-and-verification.md`.

## Prerequisites

| Secret / flag | Used by | Placeholder only until ops provides |
| --- | --- | --- |
| `ZOOM_CLIENT_ID` / `ZOOM_CLIENT_SECRET` + connected OAuth | Zoom list / recordings / webhook | yes |
| `ZOOM_WEBHOOK_SECRET_TOKEN` | `/webhooks/zoom` signature | yes |
| `ZOOM_HOST_ORG_MAP` or `ZOOM_DEFAULT_ORGANISATION_ID` | Production webhook tenancy | yes |
| Microsoft Graph OAuth (`teams_graph` / OneDrive) | Teams calendar + recordings | yes |
| `TEAMS_BOT_APP_ID` / `TEAMS_BOT_APP_SECRET` / `TEAMS_BOT_TENANT_ID` / `TEAMS_BOT_CALLBACK_URI` | Live Teams calling bot | yes |
| `ZOOM_MEETING_SDK_KEY` / `ZOOM_MEETING_SDK_SECRET` | Live Zoom Meeting SDK bot | yes |
| Local Whisper / `WHISPER_MODEL=large-v3` or Intron Sahara | Kiswahili ASR | yes |
| `HAKISCRIBE_VERIFY_ZOOM=1` / `HAKISCRIBE_VERIFY_TEAMS=1` / `HAKISCRIBE_VERIFY_ASR=1` | Opt-in live scripts | — |

## Scripts

```bash
# From hakiscribe-backend/
python scripts/verify_court_adapters_sandbox.py   # skips unless HAKISCRIBE_VERIFY_ZOOM/TEAMS=1
python scripts/verify_asr_wer.py                  # skips unless HAKISCRIBE_VERIFY_ASR=1
```

Contract tests (always safe):

```bash
pytest tests/test_court_adapters.py tests/test_live_bots.py tests/test_production_hearings.py -q
```

## Checklists

- [zoom-teams-checklist.md](./zoom-teams-checklist.md)
- [kiswahili-asr-checklist.md](./kiswahili-asr-checklist.md)
