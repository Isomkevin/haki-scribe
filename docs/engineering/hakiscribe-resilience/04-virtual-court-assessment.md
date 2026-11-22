# 04 — Virtual court assessment

## Platforms

| Platform | Official path | Stage A | Stage B+ |
| --- | --- | --- | --- |
| Google Calendar (+ Meet links in events) | Calendar API via existing OAuth | Import hearing-like events; attach Meet URL metadata | Meet recording ingest if authorized |
| Microsoft Teams | Graph OnlineMeetings / Calendar; extend OneDrive Microsoft app scopes | List/get meeting metadata; OAuth scope docs | Consented capture / recording download |
| Zoom | Zoom OAuth + Meetings / Recordings APIs | Connector + list stubs | Recording download + webhook |
| Manual upload | Local file | Full | — |

## Constraints

- Do **not** fabricate bot join capability.
- Recording access depends on org admin policy and consent.
- Kenyan virtual courts often use Teams/Zoom; Calendar remains the scheduling backbone.
- Ambiguous matter matches require human confirmation — never silent attach.

## Building blocks already in repo

- Google Calendar OAuth (`oauth.py`, connectors)
- Microsoft OneDrive OAuth (Graph files — extend scopes carefully)
- Action Tray `calendar_event` + `.ics` + HakiChain `file_reminder`
- Matter registry + `file_matter`
