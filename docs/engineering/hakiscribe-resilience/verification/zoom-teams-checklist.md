# Zoom / Teams verification checklist

## OAuth & scopes

### Zoom

- [ ] Marketplace OAuth app with `meeting:read:list_meetings`, cloud recording read scopes
- [ ] Connect via Settings → Connectors (`zoom`)
- [ ] `GET`-equivalent: `POST /hearings/import/zoom` returns upcoming meetings
- [ ] Event subscription `recording.completed` → `/webhooks/zoom` with `ZOOM_WEBHOOK_SECRET_TOKEN`
- [ ] URL validation challenge succeeds
- [ ] Production: `ZOOM_HOST_ORG_MAP` maps `host_id` → organisation UUID

### Teams (Graph)

- [ ] App registration with OnlineMeetings, Calendars.Read, transcript/recording read (admin consent)
- [ ] Connect `teams_graph` or Microsoft OneDrive OAuth
- [ ] `POST /hearings/import/teams` lists online meetings
- [ ] `POST /hearings/{id}/fetch-recording?prefer=transcript` returns VTT when organizer + recording enabled

### Live bots (ADR-015)

- [ ] Teams: `TEAMS_BOT_*` + `TEAMS_BOT_CALLBACK_URI`; admin consent for Calls.JoinGroupCall.All
- [ ] Zoom: `ZOOM_MEETING_SDK_KEY` / `ZOOM_MEETING_SDK_SECRET`; host admits bot
- [ ] Tracker **Start capture** / **Stop capture** on matched Teams/Zoom hearing
- [ ] Lifecycle: `matched` → `capturing` → `ingested` after finalize

## Expected hearing outcomes

| Step | Expected status / field |
| --- | --- |
| Import | `scheduled` / `pending_confirm` + candidates |
| Confirm matter | `matched` (or `ingested` if recording already present) |
| Upload / fetch / webhook | `recording_object_key` set; `ingested` when matched |
| Process (queued) | `pipeline.state` queued → running → done; status `transcribed` |
| Review | `reviewed` |

## Sandbox script

```bash
set HAKISCRIBE_VERIFY_ZOOM=1
set HAKISCRIBE_VERIFY_TEAMS=1
python scripts/verify_court_adapters_sandbox.py
```

Paste pass/fail into `09-testing-and-verification.md` under **1B**. Do not mark verified without a real tenant run.
