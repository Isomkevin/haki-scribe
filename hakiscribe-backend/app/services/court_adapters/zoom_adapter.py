"""Zoom Meetings API adapter — Stage A OAuth + list stub.

Recording download and webhooks are Stage B. Does not fabricate meeting bots.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.court_adapters.base import CourtAdapter, HearingEvent


class ZoomAdapter(CourtAdapter):
    source = "zoom"

    def configured(self) -> bool:
        from app.services import integrations

        creds = integrations.get_creds("zoom") or {}
        return bool(creds.get("access_token") or creds.get("refresh_token"))

    def capability_notes(self) -> dict[str, Any]:
        notes = super().capability_notes()
        notes.update(
            {
                "oauth": True,
                "list_meetings": True,
                "live_bot_join": False,
                "recording_download": False,
                "stage_b": "cloud recording download + webhooks",
                "oauth_scopes": ["meeting:read:list_meetings", "cloud_recording:read:list_user_recordings"],
            }
        )
        return notes

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        from app.services import integrations

        if not self.configured():
            return []
        creds = await integrations.get_fresh_creds("zoom") or {}
        token = (creds.get("access_token") or "").strip()
        if not token:
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.zoom.us/v2/users/me/meetings",
                headers={"Authorization": f"Bearer {token}"},
                params={"type": "upcoming", "page_size": 50},
            )
            if resp.status_code >= 400:
                return []
            body = resp.json()

        events: list[HearingEvent] = []
        for item in body.get("meetings") or []:
            title = str(item.get("topic") or "Zoom meeting")
            start = _parse(item.get("start_time"))
            events.append(
                HearingEvent(
                    external_id=str(item.get("id") or title),
                    title=title,
                    description=str(item.get("agenda") or ""),
                    starts_at=start,
                    meeting_url=item.get("join_url"),
                    metadata={"uuid": item.get("uuid"), "duration": item.get("duration")},
                )
            )
        return events


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
