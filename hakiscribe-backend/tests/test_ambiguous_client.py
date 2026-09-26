import asyncio
import unittest

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
