"""Google Calendar hearing import via existing OAuth connector."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.services.court_adapters.base import CourtAdapter, HearingEvent

HEARING_HINT = re.compile(
    r"\b(hearing|mention|mention date|virtual court|teams|zoom|meet|cause list|ruling)\b",
    re.I,
)


class GoogleCalendarAdapter(CourtAdapter):
    source = "google_calendar"

    def configured(self) -> bool:
        from app.services import integrations

        creds = integrations.get_creds("google_calendar") or {}
        return bool(creds.get("access_token") or creds.get("refresh_token"))

    def capability_notes(self) -> dict[str, Any]:
        notes = super().capability_notes()
        notes.update(
            {
                "import_events": True,
                "meet_url_from_event": True,
                "recording_download": False,
            }
        )
        return notes

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        from app.services import integrations

        if not self.configured():
            return []
        creds = await integrations.get_fresh_creds("google_calendar") or {}
        token = (creds.get("access_token") or "").strip()
        if not token:
            return []

        now = datetime.now(timezone.utc)
        time_min = now.isoformat().replace("+00:00", "Z")
        time_max = (now + timedelta(days=days)).isoformat().replace("+00:00", "Z")
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "50",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            if resp.status_code >= 400:
                return []
            body = resp.json()

        events: list[HearingEvent] = []
        for item in body.get("items") or []:
            title = str(item.get("summary") or "Untitled event")
            description = str(item.get("description") or "")
            hay = f"{title}\n{description}"
            has_conference = bool(item.get("hangoutLink") or (item.get("conferenceData") or {}).get("entryPoints"))
            if not HEARING_HINT.search(hay) and not has_conference:
                continue
            start = _parse_time((item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"))
            end = _parse_time((item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date"))
            meeting_url = item.get("hangoutLink")
            for ep in ((item.get("conferenceData") or {}).get("entryPoints") or []):
                if ep.get("uri"):
                    meeting_url = meeting_url or ep.get("uri")
                    break
            events.append(
                HearingEvent(
                    external_id=str(item.get("id") or title),
                    title=title,
                    description=description,
                    starts_at=start,
                    ends_at=end,
                    meeting_url=meeting_url,
                    metadata={"htmlLink": item.get("htmlLink"), "raw_status": item.get("status")},
                )
            )
        return events


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if len(value) == 10:
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
