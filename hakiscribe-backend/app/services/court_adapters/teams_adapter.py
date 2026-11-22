"""Microsoft Teams via Graph (delegated OAuth only).

- list_upcoming: GET /me/calendarView (online meetings in the user's calendar)
- fetch_artifact: resolve the online meeting from its join URL, then pull the
  Teams transcript (WebVTT with participant names) or the recording (MP4):
    GET /me/onlineMeetings?$filter=JoinWebUrl eq '<url>'
    GET /me/onlineMeetings/{id}/transcripts      → .../{tid}/content?$format=text/vtt
    GET /me/onlineMeetings/{id}/recordings       → .../{rid}/content

Graph constraints (documented, not worked around):
- /me/onlineMeetings only returns meetings the signed-in user organised.
- Transcripts need OnlineMeetingTranscript.Read.All and recordings need
  OnlineMeetingRecording.Read.All — both require tenant admin consent.
- Transcription/recording must have been switched on in the meeting.
Does not join meetings as a bot; that needs a Teams calling bot registration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.services.court_adapters.base import AdapterError, CourtAdapter, HearingArtifact, HearingEvent, http_client

GRAPH = "https://graph.microsoft.com/v1.0"


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
                    "OnlineMeetingTranscript.Read.All",
                    "OnlineMeetingRecording.Read.All",
                ],
                "admin_consent_required": True,
                "organizer_only": True,
                "live_bot_join": False,  # see TeamsCallingBot when TEAMS_BOT_* is set
                "recording_download": True,
                "transcript_download": True,
                "stage": "B",
                "companion_bot": "teams_calling_bot",
            }
        )
        return notes

    async def _token(self) -> str:
        from app.services import integrations

        for pid in ("teams_graph", "onedrive"):
            creds = await integrations.get_fresh_creds(pid)
            token = ((creds or {}).get("access_token") or "").strip()
            if token:
                return token
        raise AdapterError("Microsoft Teams Graph is not connected")

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        if not self.configured():
            return []
        try:
            token = await self._token()
        except AdapterError:
            return []

        # Calendar view is the most widely permitted Graph surface for meetings.
        async with http_client() as client:
            resp = await client.get(
                f"{GRAPH}/me/calendarView",
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

    async def _get(self, client, url: str, token: str, *, params: Optional[dict] = None, what: str):
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        if resp.status_code in (401, 403):
            raise AdapterError(
                f"Graph denied {what} — needs admin-consented OnlineMeeting* scopes and the "
                "signed-in user must be the meeting organiser",
                status=resp.status_code,
            )
        if resp.status_code == 404:
            raise AdapterError(f"Graph found no {what}", status=404)
        if resp.status_code >= 400:
            raise AdapterError(f"Graph {what} returned {resp.status_code}", status=resp.status_code)
        return resp

    async def resolve_meeting_id(self, join_url: str, token: str) -> str:
        escaped = join_url.replace("'", "''")
        async with http_client() as client:
            resp = await self._get(
                client,
                f"{GRAPH}/me/onlineMeetings",
                token,
                params={"$filter": f"JoinWebUrl eq '{escaped}'"},
                what="online meeting",
            )
        items = resp.json().get("value") or []
        if not items:
            raise AdapterError("No online meeting organised by this user matches the hearing's join URL", status=404)
        return str(items[0]["id"])

    async def fetch_artifact(self, hearing: Any, *, prefer: str = "transcript") -> HearingArtifact:
        if not hearing.meeting_url:
            raise AdapterError("Hearing has no Teams join URL")
        token = await self._token()
        meeting_id = await self.resolve_meeting_id(hearing.meeting_url, token)
        base = f"{GRAPH}/me/onlineMeetings/{meeting_id}"
        order = ("transcript", "audio") if prefer != "audio" else ("audio", "transcript")
        errors: list[str] = []
        async with http_client(timeout=600.0) as client:
            for kind in order:
                collection = "transcripts" if kind == "transcript" else "recordings"
                try:
                    listing = await self._get(client, f"{base}/{collection}", token, what=collection)
                    items = sorted(listing.json().get("value") or [], key=lambda i: i.get("createdDateTime") or "")
                    if not items:
                        errors.append(f"no {collection} for this meeting")
                        continue
                    latest = items[-1]
                    params = {"$format": "text/vtt"} if kind == "transcript" else None
                    content = await self._get(
                        client, f"{base}/{collection}/{latest['id']}/content", token, params=params, what=f"{kind} content"
                    )
                except AdapterError as exc:
                    errors.append(str(exc))
                    continue
                return HearingArtifact(
                    kind=kind,
                    filename=f"teams-{latest['id'][:24]}.{'vtt' if kind == 'transcript' else 'mp4'}",
                    data=content.content,
                    content_type="text/vtt" if kind == "transcript" else content.headers.get("content-type", "video/mp4"),
                    metadata={"online_meeting_id": meeting_id, f"{kind}_id": latest["id"]},
                )
        raise AdapterError("; ".join(errors) or "No transcript or recording available")


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
