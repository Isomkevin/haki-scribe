"""Zoom Meetings + Cloud Recording APIs (official OAuth only).

- list_upcoming: GET /users/me/meetings?type=upcoming
- fetch_artifact: GET /meetings/{id}/recordings, then download the audio-only
  file (or the VTT transcript) with the user's OAuth token
- webhook: `recording.completed` (see routers/court_webhooks.py) carries a
  short-lived `download_token` so recordings arrive without polling

Requires the cloud recording to exist and the OAuth app to hold recording
scopes. Does not join meetings or capture live audio — Zoom offers no
official API for that to third-party apps without the Meeting SDK bot model.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote

from app.services.court_adapters.base import AdapterError, CourtAdapter, HearingArtifact, HearingEvent, http_client

API = "https://api.zoom.us/v2"

# Preference order within each kind.
_AUDIO_TYPES = ("M4A", "MP4")
_TRANSCRIPT_TYPES = ("TRANSCRIPT",)


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
                "recording_download": True,
                "recording_webhook": True,
                "stage": "B",
                "oauth_scopes": [
                    "meeting:read:list_meetings",
                    "cloud_recording:read:list_recording_files",
                    "cloud_recording:read:list_user_recordings",
                ],
                "requirements": "Cloud recording enabled on the host account; audio transcript optional.",
            }
        )
        return notes

    async def _token(self) -> str:
        from app.services import integrations

        creds = await integrations.get_fresh_creds("zoom") or {}
        token = (creds.get("access_token") or "").strip()
        if not token:
            raise AdapterError("Zoom is not connected")
        return token

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        if not self.configured():
            return []
        try:
            token = await self._token()
        except AdapterError:
            return []

        async with http_client() as client:
            resp = await client.get(
                f"{API}/users/me/meetings",
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

    async def get_recordings(self, meeting_id: str) -> dict[str, Any]:
        token = await self._token()
        # Meeting UUIDs that start with "/" or contain "//" must be double-encoded.
        mid = quote(quote(meeting_id, safe=""), safe="") if "/" in meeting_id else meeting_id
        async with http_client() as client:
            resp = await client.get(f"{API}/meetings/{mid}/recordings", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 404:
            raise AdapterError("Zoom has no cloud recording for this meeting yet", status=404)
        if resp.status_code in (401, 403):
            raise AdapterError("Zoom denied recording access — check cloud_recording scopes", status=resp.status_code)
        if resp.status_code >= 400:
            raise AdapterError(f"Zoom recordings API returned {resp.status_code}", status=resp.status_code)
        return resp.json()

    async def fetch_artifact(self, hearing: Any, *, prefer: str = "audio") -> HearingArtifact:
        if not hearing.external_id:
            raise AdapterError("Hearing has no Zoom meeting id")
        recording = await self.get_recordings(str(hearing.external_id))
        token = await self._token()
        return await download_preferred(recording.get("recording_files") or [], token, prefer=prefer, meeting=recording)


def pick_recording_file(files: list[dict[str, Any]], *, prefer: str = "audio") -> Optional[dict[str, Any]]:
    ready = [f for f in files if (f.get("status") or "completed").lower() == "completed" and f.get("download_url")]
    by_type = {str(f.get("file_type") or "").upper(): f for f in ready}
    order = (_AUDIO_TYPES + _TRANSCRIPT_TYPES) if prefer == "audio" else (_TRANSCRIPT_TYPES + _AUDIO_TYPES)
    for t in order:
        if t in by_type:
            return by_type[t]
    return None


async def download_preferred(
    files: list[dict[str, Any]],
    token: str,
    *,
    prefer: str = "audio",
    meeting: Optional[dict[str, Any]] = None,
) -> HearingArtifact:
    chosen = pick_recording_file(files, prefer=prefer)
    if chosen is None:
        raise AdapterError("No completed audio or transcript file in this Zoom recording")
    file_type = str(chosen.get("file_type") or "").upper()
    async with http_client(timeout=600.0) as client:
        resp = await client.get(str(chosen["download_url"]), headers={"Authorization": f"Bearer {token}"})
    if resp.status_code >= 400:
        raise AdapterError(f"Zoom recording download returned {resp.status_code}", status=resp.status_code)
    is_transcript = file_type in _TRANSCRIPT_TYPES
    ext = "vtt" if is_transcript else str(chosen.get("file_extension") or file_type).lower()
    return HearingArtifact(
        kind="transcript" if is_transcript else "audio",
        filename=f"zoom-{chosen.get('id') or 'recording'}.{ext}",
        data=resp.content,
        content_type="text/vtt" if is_transcript else resp.headers.get("content-type", "application/octet-stream"),
        metadata={
            "zoom_file_id": chosen.get("id"),
            "file_type": file_type,
            "recording_type": chosen.get("recording_type"),
            "meeting_uuid": (meeting or {}).get("uuid"),
        },
    )


def webhook_secret() -> str:
    import os

    return (os.environ.get("ZOOM_WEBHOOK_SECRET_TOKEN") or "").strip()


def sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_webhook(secret: str, *, signature: str, timestamp: str, body: bytes, max_skew_s: int = 300) -> bool:
    """Zoom signs `v0:{timestamp}:{raw body}` with HMAC-SHA256 → header `v0=<hex>`."""
    if not (secret and signature and timestamp):
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if ts > 10**12:  # tolerate millisecond timestamps
        ts //= 1000
    if abs(time.time() - ts) > max_skew_s:
        return False
    expected = "v0=" + sign(secret, f"v0:{timestamp}:{body.decode('utf-8')}")
    return hmac.compare_digest(expected, signature)


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
