import unittest
from unittest.mock import AsyncMock, patch

from app.integrations import hakichain_client
from app.services import integrations


class HakiChainClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_me_failure_is_not_ok(self):
        with patch("httpx.AsyncClient") as client_cls, patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
            },
            clear=False,
        ):
            client = AsyncMock()
            response = AsyncMock()
            response.status_code = 401
            response.text = "Unknown HakiScribe token"
            response.content = b'{"error":"Unknown HakiScribe token"}'
            response.json = lambda: {"error": "Unknown HakiScribe token"}
            client.__aenter__.return_value = client
            client.post.return_value = response
            client_cls.return_value = client

            result = await hakichain_client.me("hkc_badtoken")
            self.assertFalse(result["ok"])
            self.assertIn("401", result["error"] or "")

    async def test_verify_does_not_accept_nonempty_without_me(self):
        with patch(
            "app.integrations.hakichain_client.me",
            new=AsyncMock(return_value={"ok": False, "error": "Unknown HakiScribe token"}),
        ):
            result = await integrations.verify("hakichain", {"api_key": "hkc_not_empty"})
            self.assertFalse(result["ok"])
            self.assertIn("Unknown", result.get("error") or "")

    async def test_file_document_returns_workspace_url(self):
        with patch.object(hakichain_client, "configured", return_value=True), patch.object(
            hakichain_client,
            "_request",
            new=AsyncMock(
                return_value={
                    "ok": True,
                    "client_id": "hs-session-1",
                    "workspace_url": "https://hakichain.com/workspace?ws=hs-session-1",
                }
            ),
        ):
            filed = await hakichain_client.file_document(
                action_key="draft:1",
                session_id="session-1",
                title="Demand letter",
                document_text="Body",
            )
            self.assertIsNotNone(filed)
            self.assertEqual(filed["client_id"], "hs-session-1")
            self.assertIn("/workspace?ws=hs-session-1", filed["workspace_url"])


if __name__ == "__main__":
    unittest.main()
