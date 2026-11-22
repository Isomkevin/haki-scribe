"""Microsoft Teams via Graph OnlineMeetings — Stage A metadata list only.

Does not join meetings as a bot. Recording download is Stage B when admin
policy and consent allow. Extends Microsoft OAuth with OnlineMeetings scopes
(document in CONNECTOR_OAUTH_SETUP / resilience pack).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.court_adapters.base import CourtAdapter, HearingEvent


class TeamsGraphAdapter(CourtAdapter):
    source = "teams_graph"

    def configured(self) -> bool:
        from app.services import integrations

        # Prefer dedicated teams_graph creds; fall back to onedrive Microsoft token.
        for pid in ("teams_graph", "onedrive"):
            creds = integrations.get_creds(pid) or {}
            if creds.get("access_token") or creds.get("refresh_token"):
                return True
        return False

    def capability_notes(self) -> dict[str, Any]:
        notes = super().capability_notes()
        notes.update(
            {
                "graph_online_meetings": True,
                "required_scopes": [
                    "OnlineMeetings.Read",
                    "Calendars.Read",
                    "User.Read",
                    "offline_access",
                ],
                "live_bot_join": False,
                "recording_download": False,
                "stage_b": "recording download + consented capture",
            }
        )
        return notes

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        from app.services import integrations

        if not self.configured():
            return []
        creds = None
        for pid in ("teams_graph", "onedrive"):
            creds = await integrations.get_fresh_creds(pid)
            if creds and creds.get("access_token"):
                break
        token = ((creds or {}).get("access_token") or "").strip()
        if not token:
            return []

        # Calendar view is the most widely permitted Graph surface for meetings.
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me/calendarView",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "startDateTime": datetime.utcnow().isoformat() + "Z",
                    "endDateTime": _end(days),
                    "$top": "50",
                    "$orderby": "start/dateTime",
                },
            )
            if resp.status_code >= 400:
                return []
            body = resp.json()

        events: list[HearingEvent] = []
        for item in body.get("value") or []:
            title = str(item.get("subject") or "Teams meeting")
            if not _looks_like_hearing(title, item.get("bodyPreview") or ""):
                if not item.get("isOnlineMeeting") and not item.get("onlineMeeting"):
                    continue
            start = _parse((item.get("start") or {}).get("dateTime"))
            end = _parse((item.get("end") or {}).get("dateTime"))
            online = item.get("onlineMeeting") or {}
            events.append(
                HearingEvent(
                    external_id=str(item.get("id") or title),
                    title=title,
                    description=str(item.get("bodyPreview") or ""),
                    starts_at=start,
                    ends_at=end,
                    meeting_url=online.get("joinUrl") or item.get("onlineMeetingUrl"),
                    metadata={"webLink": item.get("webLink"), "isOnlineMeeting": item.get("isOnlineMeeting")},
                )
            )
        return events


def _end(days: int) -> str:
    from datetime import timedelta

    return (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _looks_like_hearing(title: str, preview: str) -> bool:
    hay = f"{title} {preview}".lower()
    return any(k in hay for k in ("hearing", "mention", "court", "ruling", "teams", "virtual"))
