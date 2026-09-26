import asyncio
import unittest
from unittest.mock import patch

from app.integrations import ambiguous_client


class AmbiguousClientConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_last_error_is_isolated_per_concurrent_task(self):
        async def worker(message: str) -> str | None:
            ambiguous_client._set_error(message)
            await asyncio.sleep(0)
            return ambiguous_client.last_error()

        first, second = await asyncio.gather(worker("first request"), worker("second request"))

        self.assertEqual(first, "first request")
        self.assertEqual(second, "second request")

    def test_connector_routing_settings_override_environment(self):
        with patch("app.services.integrations.get_creds") as get_creds, patch.dict(
            "os.environ",
            {
                "AMBIGUOUS_CALENDAR_ID": "environment-calendar",
                "AMBIGUOUS_NOTIFY_CHANNEL": "environment-channel",
            },
            clear=False,
        ):
            get_creds.return_value = {
                "api_key": "ak_test",
                "calendar_id": "connector-calendar",
                "notify_channel": "connector-channel",
            }
            self.assertEqual(
                ambiguous_client._connector_setting("calendar_id", "AMBIGUOUS_CALENDAR_ID"),
                "connector-calendar",
            )
            self.assertEqual(
                ambiguous_client._connector_setting("notify_channel", "AMBIGUOUS_NOTIFY_CHANNEL"),
                "connector-channel",
            )
