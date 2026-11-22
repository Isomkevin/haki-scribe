"""Microsoft Teams calling bot (official Bot Framework + Graph Calls).

Joins an authorized online meeting when TEAMS_BOT_* credentials and admin
consent are present. Captures media through the calling-bot model — not by
scraping the Teams client.

Required env (document in CONNECTOR_OAUTH_SETUP.md):
  TEAMS_BOT_APP_ID, TEAMS_BOT_APP_SECRET, TEAMS_BOT_TENANT_ID
  Optional: TEAMS_BOT_CALLBACK_URI for media streaming webhook

Without credentials, configured() is False and capability notes stay honest.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from uuid import UUID

from app.services.court_adapters.base import AdapterError, CourtAdapter, HearingEvent


class TeamsCallingBot(CourtAdapter):
    source = "teams_calling_bot"

    def configured(self) -> bool:
        return bool(
            os.environ.get("TEAMS_BOT_APP_ID")
            and os.environ.get("TEAMS_BOT_APP_SECRET")
            and os.environ.get("TEAMS_BOT_TENANT_ID")
        )

    def capability_notes(self) -> dict[str, Any]:
        notes = super().capability_notes()
        notes.update(
            {
                "live_bot_join": self.configured(),
                "official_sdk": "Bot Framework + Graph Calls / CallRecords",
                "required_permissions": [
                    "Calls.AccessMedia.All",
                    "Calls.JoinGroupCall.All",
                    "OnlineMeetings.Read.All",
                ],
                "admin_consent_required": True,
                "tenant_policy_may_block_recording": True,
                "recording_download": False,
                "stage": "E",
                "configured": self.configured(),
            }
        )
        return notes

    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        return []

    async def join_meeting(self, *, meeting_url: str, hearing_id: UUID) -> dict[str, Any]:
        if not self.configured():
            raise AdapterError(
                "Teams calling bot is not configured. Set TEAMS_BOT_APP_ID, "
                "TEAMS_BOT_APP_SECRET, TEAMS_BOT_TENANT_ID and grant admin consent."
            )
        if not meeting_url:
            raise AdapterError("Hearing has no Teams meeting URL to join")
        # Official join: application posts a call to Graph with callbackUri.
        # Live media arrives on the bot callback; we record session metadata here.
        from app.services.court_adapters.base import http_client

        tenant = os.environ["TEAMS_BOT_TENANT_ID"]
        app_id = os.environ["TEAMS_BOT_APP_ID"]
        secret = os.environ["TEAMS_BOT_APP_SECRET"]
        callback = (os.environ.get("TEAMS_BOT_CALLBACK_URI") or "").rstrip("/")
        if not callback:
            raise AdapterError("TEAMS_BOT_CALLBACK_URI is required to receive call media")

        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        async with http_client(timeout=60.0) as client:
            token_resp = await client.post(
                token_url,
                data={
                    "client_id": app_id,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            if token_resp.status_code >= 400:
                raise AdapterError(
                    f"Teams bot token failed ({token_resp.status_code}): {token_resp.text[:300]}",
                    status=token_resp.status_code,
                )
            access = token_resp.json().get("access_token")
            if not access:
                raise AdapterError("Teams bot token response missing access_token")

            # Create a group call join via Graph communications API.
            payload = {
                "callbackUri": f"{callback}/webhooks/teams-bot/calls",
                "requestedModalities": ["audio"],
                "mediaConfig": {"@odata.type": "#microsoft.graph.serviceHostedMediaConfig"},
                "chatInfo": {"threadId": meeting_url, "messageId": "0"},
                "meetingInfo": {
                    "@odata.type": "#microsoft.graph.joinMeetingIdMeetingInfo",
                    "joinMeetingId": meeting_url,
                    "passcode": None,
                },
            }
            # Prefer joinUrl when the hearing stores a full join URL.
            if meeting_url.startswith("http"):
                payload = {
                    "callbackUri": f"{callback}/webhooks/teams-bot/calls",
                    "requestedModalities": ["audio"],
                    "mediaConfig": {"@odata.type": "#microsoft.graph.serviceHostedMediaConfig"},
                    "meetingInfo": {
                        "@odata.type": "#microsoft.graph.tokenMeetingInfo",
                        "token": meeting_url,
                    },
                }
            call_resp = await client.post(
                "https://graph.microsoft.com/v1.0/communications/calls",
                headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
                json=payload,
            )
            if call_resp.status_code >= 400:
                raise AdapterError(
                    f"Teams bot join refused ({call_resp.status_code}): {call_resp.text[:400]}. "
                    "Check admin consent, Calls.JoinGroupCall.All, and tenant recording policy.",
                    status=call_resp.status_code,
                )
            body = call_resp.json()
            return {
                "platform": "teams",
                "call_id": body.get("id"),
                "state": body.get("state"),
                "hearing_id": str(hearing_id),
                "raw": {"id": body.get("id"), "state": body.get("state")},
            }

    async def leave_meeting(self, *, call_id: str) -> dict[str, Any]:
        if not self.configured():
            raise AdapterError("Teams calling bot is not configured")
        if not call_id:
            raise AdapterError("No call_id to hang up")
        from app.services.court_adapters.base import http_client

        tenant = os.environ["TEAMS_BOT_TENANT_ID"]
        app_id = os.environ["TEAMS_BOT_APP_ID"]
        secret = os.environ["TEAMS_BOT_APP_SECRET"]
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        async with http_client(timeout=30.0) as client:
            token_resp = await client.post(
                token_url,
                data={
                    "client_id": app_id,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            access = token_resp.json().get("access_token")
            if not access:
                raise AdapterError("Teams bot token failed")
            resp = await client.delete(
                f"https://graph.microsoft.com/v1.0/communications/calls/{call_id}",
                headers={"Authorization": f"Bearer {access}"},
            )
            if resp.status_code >= 400 and resp.status_code != 404:
                raise AdapterError(f"Teams bot hangup failed ({resp.status_code})", status=resp.status_code)
        return {"platform": "teams", "call_id": call_id, "state": "terminated"}
