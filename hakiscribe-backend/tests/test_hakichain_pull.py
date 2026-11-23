"""HakiChain pull/link client actions (contract 2026-11)."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations import hakichain_client


class HakiChainPullTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_matters_posts_contract_version(self):
        with patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
            },
            clear=False,
        ), patch("app.services.integrations.get_creds") as get_creds:
            get_creds.return_value = {"api_key": "hkc_live_token"}
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"ok":true}'
            mock_response.json.return_value = {
                "ok": True,
                "matters": [
                    {
                        "workspace_id": "11111111-1111-1111-1111-111111111111",
                        "client_id": "ws-acme",
                        "name": "Lease",
                        "client": "Acme",
                        "role": "owner",
                    }
                ],
            }
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await hakichain_client.list_matters()

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result["matters"]), 1)
        payload = mock_client.post.await_args.kwargs["json"]
        self.assertEqual(payload["action"], "list_matters")
        self.assertEqual(payload["contract_version"], "2026-11")

    async def test_link_matter_payload(self):
        with patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
            },
            clear=False,
        ), patch("app.services.integrations.get_creds") as get_creds:
            get_creds.return_value = {"api_key": "hkc_live_token"}
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"ok":true}'
            mock_response.json.return_value = {
                "ok": True,
                "client_id": "ws-acme",
                "workspace_id": "11111111-1111-1111-1111-111111111111",
                "workspace_url": "https://hakichain.com/workspace?ws=ws-acme",
            }
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await hakichain_client.link_matter(
                    action_key="link:matter-1",
                    workspace_id="11111111-1111-1111-1111-111111111111",
                    scribe_matter_id="matter-1",
                )

        self.assertEqual(result["client_id"], "ws-acme")
        payload = mock_client.post.await_args.kwargs["json"]
        self.assertEqual(payload["action"], "link_matter")
        self.assertEqual(payload["contract_version"], "2026-11")

    async def test_finalize_transcript_payload(self):
        with patch.dict(
            "os.environ",
            {
                "HAKICHAIN_API_BASE": "https://example.supabase.co/functions/v1/hakiscribe-ingress",
                "HAKICHAIN_SUPABASE_ANON_KEY": "anon-test",
            },
            clear=False,
        ), patch("app.services.integrations.get_creds") as get_creds:
            get_creds.return_value = {"api_key": "hkc_live_token"}
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"ok":true}'
            mock_response.json.return_value = {"ok": True, "hearing_id": "h1", "segments": 1}
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await hakichain_client.finalize_transcript(
                    action_key="hearing-finalize:h",
                    scribe_hearing_id="h",
                    workspace_id="11111111-1111-1111-1111-111111111111",
                    segments=[{"text": "Hello", "start_ms": 0, "end_ms": 100, "redacted": False}],
                    proceedings={"rules": []},
                    title="Mention",
                )

        self.assertTrue(result["ok"])
        payload = mock_client.post.await_args.kwargs["json"]
        self.assertEqual(payload["action"], "finalize_transcript")
        self.assertEqual(len(payload["segments"]), 1)


if __name__ == "__main__":
    unittest.main()
