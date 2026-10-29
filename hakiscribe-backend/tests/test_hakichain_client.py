import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations import hakichain_client
from app.services import integrations


class HakiChainClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_me_failure_is_not_ok(self):
        with patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
            },
            clear=False,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unknown HakiScribe token"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await hakichain_client.me("hkc_bad_token")

        self.assertFalse(result["ok"])
        self.assertIn("401", result["error"] or "")

        verify = await integrations._verify_hakichain({"api_key": "hkc_bad_token"})
        self.assertFalse(verify["ok"])

    async def test_file_matter_returns_workspace_url(self):
        with patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
                "HAKICHAIN_APP_ORIGIN": "https://hakichain.com",
            },
            clear=False,
        ), patch("app.services.integrations.get_creds") as get_creds:
            get_creds.return_value = {"api_key": "hkc_live_token"}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"ok":true}'
            mock_response.json.return_value = {
                "ok": True,
                "client_id": "hs-matter-1",
                "workspace_url": "https://hakichain.com/workspace?ws=hs-matter-1",
            }

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                filed = await hakichain_client.file_matter(
                    action_key="matter:test",
                    scribe_matter_id="matter-1",
                    matter_name="Kamau v Republic",
                    client_name="Kamau",
                )

        self.assertIsNotNone(filed)
        assert filed is not None
        self.assertEqual(filed["client_id"], "hs-matter-1")
        self.assertEqual(
            filed["workspace_url"],
            "https://hakichain.com/workspace?ws=hs-matter-1",
        )
        self.assertEqual(
            hakichain_client.workspace_url("hs-matter-1"),
            "https://hakichain.com/workspace?ws=hs-matter-1",
        )

    async def test_verify_success_stores_account_on_creds(self):
        creds = {"api_key": "hkc_good"}
        with patch("app.integrations.hakichain_client.me", new_callable=AsyncMock) as me:
            me.return_value = {"ok": True, "error": None, "account": "Jane Advocate"}
            result = await integrations._verify_hakichain(creds)
        self.assertTrue(result["ok"])
        self.assertEqual(creds.get("account"), "Jane Advocate")


if __name__ == "__main__":
    unittest.main()
