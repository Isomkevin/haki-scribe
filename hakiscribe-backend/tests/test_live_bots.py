"""Contract tests for official Teams calling-bot and Zoom Meeting SDK adapters."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.schemas import Hearing, HearingSource, HearingStatus
from app.services.court_adapters import live_capture, teams_bot, zoom_bot
from app.services.court_adapters.base import AdapterError


class LiveBotContractTests(unittest.IsolatedAsyncioTestCase):
    def test_bots_unconfigured_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            for key in (
                "TEAMS_BOT_APP_ID",
                "TEAMS_BOT_APP_SECRET",
                "TEAMS_BOT_TENANT_ID",
                "ZOOM_MEETING_SDK_KEY",
                "ZOOM_MEETING_SDK_SECRET",
            ):
                # Ensure unset for this assertion path
                pass
            with patch.dict(
                "os.environ",
                {
                    "TEAMS_BOT_APP_ID": "",
                    "TEAMS_BOT_APP_SECRET": "",
                    "TEAMS_BOT_TENANT_ID": "",
                    "ZOOM_MEETING_SDK_KEY": "",
                    "ZOOM_MEETING_SDK_SECRET": "",
                },
                clear=False,
            ):
                self.assertFalse(teams_bot.TeamsCallingBot().configured())
                self.assertFalse(zoom_bot.ZoomMeetingBot().configured())
                notes = teams_bot.TeamsCallingBot().capability_notes()
                self.assertFalse(notes["live_bot_join"])
                self.assertTrue(notes["admin_consent_required"])

    async def test_zoom_signature_when_configured(self) -> None:
        with patch.dict(
            "os.environ",
            {"ZOOM_MEETING_SDK_KEY": "sdk_key", "ZOOM_MEETING_SDK_SECRET": "sdk_secret"},
            clear=False,
        ):
            bot = zoom_bot.ZoomMeetingBot()
            self.assertTrue(bot.configured())
            join = await bot.join_meeting(
                meeting_url="https://zoom.us/j/12345678901",
                hearing_id=uuid4(),
            )
            self.assertEqual(join["platform"], "zoom")
            self.assertEqual(join["meeting_number"], "12345678901")
            self.assertIn("signature", join)
            self.assertTrue(join["signature"].count(".") >= 2)

    async def test_start_capture_refuses_without_matter(self) -> None:
        hearing = Hearing(
            source=HearingSource.zoom,
            title="Test",
            meeting_url="https://zoom.us/j/1",
            status=HearingStatus.matched,
            matter_id=None,
        )
        with self.assertRaises(live_capture.CaptureError):
            await live_capture.start_capture(hearing)

    async def test_teams_join_requires_callback(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TEAMS_BOT_APP_ID": "app",
                "TEAMS_BOT_APP_SECRET": "secret",
                "TEAMS_BOT_TENANT_ID": "tenant",
                "TEAMS_BOT_CALLBACK_URI": "",
            },
            clear=False,
        ):
            bot = teams_bot.TeamsCallingBot()
            with self.assertRaises(AdapterError) as ctx:
                await bot.join_meeting(meeting_url="https://teams.microsoft.com/l/meetup-join/x", hearing_id=uuid4())
            self.assertIn("TEAMS_BOT_CALLBACK_URI", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
