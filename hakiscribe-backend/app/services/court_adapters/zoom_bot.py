"""Zoom Meeting SDK bot (official join + authorized audio capture).

Requires a Zoom Marketplace Meeting SDK app with host consent. Env:
  ZOOM_MEETING_SDK_KEY, ZOOM_MEETING_SDK_SECRET
  Optional: ZOOM_BOT_DISPLAY_NAME (default HakiScribe Capture)

Does not scrape the Zoom client. Without SDK credentials, configured() is False.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from typing import Any, Optional
from uuid import UUID

from app.services.court_adapters.base import AdapterError, CourtAdapter, HearingEvent


def _meeting_number_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/j/(\d+)", url)
    if m:
        return m.group(1)
    digits = "".join(ch for ch in url if ch.isdigit())
    return digits or None


class ZoomMeetingBot(CourtAdapter):
    source = "zoom_meeting_bot"

    def configured(self) -> bool:
        return bool(os.environ.get("ZOOM_MEETING_SDK_KEY") and os.environ.get("ZOOM_MEETING_SDK_SECRET"))

    def capability_notes(self) -> dict[str, Any]:
        notes = super().capability_notes()
        notes.update(
            {
                "live_bot_join": self.configured(),
                "official_sdk": "Zoom Meeting SDK",
                "host_consent_required": True,
                "oauth_scopes": ["meeting:write:meeting", "meeting:read:meeting"],
                "recording_download": False,
                "stage": "E",
                "configured": self.configured(),
            }
        )
        return notes

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        return []

    def _signature(self, meeting_number: str, role: int = 0) -> dict[str, Any]:
        sdk_key = os.environ["ZOOM_MEETING_SDK_KEY"]
        sdk_secret = os.environ["ZOOM_MEETING_SDK_SECRET"]
        iat = int(time.time()) - 30
        exp = iat + 60 * 60 * 2
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
        payload_obj = {
            "sdkKey": sdk_key,
            "mn": meeting_number,
            "role": role,
            "iat": iat,
            "exp": exp,
            "tokenExp": exp,
        }
        payload = base64.urlsafe_b64encode(json.dumps(payload_obj, separators=(",", ":")).encode()).rstrip(b"=").decode()
        signing_input = f"{header}.{payload}".encode()
        sig = hmac.new(sdk_secret.encode(), signing_input, hashlib.sha256).digest()
        signature = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        return {
            "sdk_key": sdk_key,
            "signature": f"{header}.{payload}.{signature}",
            "meeting_number": meeting_number,
            "role": role,
            "exp": exp,
        }

    async def join_meeting(
        self,
        *,
        meeting_url: str,
        hearing_id: UUID,
        meeting_number: Optional[str] = None,
    ) -> dict[str, Any]:
        if not self.configured():
            raise AdapterError(
                "Zoom Meeting SDK bot is not configured. Set ZOOM_MEETING_SDK_KEY and ZOOM_MEETING_SDK_SECRET."
            )
        number = meeting_number or _meeting_number_from_url(meeting_url)
        if not number:
            raise AdapterError("Could not resolve Zoom meeting number from hearing")
        creds = self._signature(number, role=0)
        display = os.environ.get("ZOOM_BOT_DISPLAY_NAME") or "HakiScribe Capture"
        return {
            "platform": "zoom",
            "meeting_number": number,
            "display_name": display,
            "sdk_key": creds["sdk_key"],
            "signature": creds["signature"],
            "hearing_id": str(hearing_id),
            "state": "joining",
            "note": "Host must admit the bot; capture streams to recording_store via bot worker.",
        }

    async def leave_meeting(self, *, meeting_number: str) -> dict[str, Any]:
        if not self.configured():
            raise AdapterError("Zoom Meeting SDK bot is not configured")
        return {"platform": "zoom", "meeting_number": meeting_number, "state": "left"}
