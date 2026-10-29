"""Privilege interception + Nebius tier resolution tests (mocked HTTP)."""

from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import ai_runs, nebius, tray_logic


MARKER = "ZEBRA-PRIVILEGED-7731"


class _Resp:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.text = str(body)

    def json(self):
        return self._body


class PrivilegeInterceptionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        ai_runs.clear()
        nebius._models_cache = {"base": None, "fetched_at": 0.0, "models": []}
        self.public = SimpleNamespace(
            id=uuid.uuid4(),
            speaker="Advocate",
            text="Mahakama imeweka mention on the twenty-eighth.",
            redacted=False,
        )
        self.priv = SimpleNamespace(
            id=uuid.uuid4(),
            speaker="Client",
            text=f"Off record: {MARKER} stays privileged.",
            redacted=True,
        )

    async def test_outbound_nebius_body_excludes_privileged_marker(self) -> None:
        captured: list[dict] = []

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, headers=None, json=None):
                captured.append({"url": url, "json": json})
                return _Resp(
                    {
                        "choices": [{"message": {"content": '{"actions":[]}'}}],
                        "model": "nvidia/nemotron-super-test",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                    }
                )

            async def get(self, url, headers=None):
                return _Resp({"data": [{"id": "nvidia/NVIDIA-Nemotron-Nano-9B-v2"}]})

        block = tray_logic.build_transcript_block([self.public, self.priv])
        self.assertNotIn(MARKER, block)

        with patch.object(nebius, "creds", return_value={"api_key": "test-key", "base_url": "https://api.tokenfactory.nebius.com/v1"}):
            with patch.object(nebius, "is_connected", return_value=True):
                with patch.object(nebius, "resolve_model", AsyncMock(return_value="nvidia/nemotron-super-test")):
                    with patch("httpx.AsyncClient", _Client):
                        await nebius.complete(
                            "super",
                            "system",
                            block,
                            task="detection",
                            privileged_lines_excluded=1,
                        )

        self.assertEqual(len(captured), 1)
        blob = str(captured[0]["json"])
        self.assertNotIn(MARKER, blob)
        self.assertNotIn("Off record", blob)
        ai_runs.assert_no_marker(MARKER)

    async def test_resolve_model_failure_lists_available_nemotron(self) -> None:
        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, headers=None):
                return _Resp(
                    {
                        "data": [
                            {"id": "nvidia/NVIDIA-Nemotron-Nano-9B-v2"},
                            {"id": "other/model"},
                        ]
                    }
                )

        with patch.object(nebius, "creds", return_value={"api_key": "test-key"}):
            with patch.object(nebius, "is_connected", return_value=True):
                with patch("httpx.AsyncClient", _Client):
                    with self.assertRaises(RuntimeError) as ctx:
                        await nebius.resolve_model("ultra")
        msg = str(ctx.exception)
        self.assertIn("ultra", msg.lower())
        self.assertIn("Nemotron models available", msg)
        self.assertIn("Nano", msg)


class IsConnectedTests(unittest.TestCase):
    def test_base_url_alone_is_not_connected(self) -> None:
        with patch.object(nebius, "creds", return_value={"base_url": "https://api.tokenfactory.nebius.com/v1"}):
            self.assertFalse(nebius.is_connected())


class SelectProviderTests(unittest.TestCase):
    def test_connected_nebius_overrides_openrouter_env(self) -> None:
        with patch.object(nebius, "is_connected", return_value=True):
            with patch.dict("os.environ", {"LLM_PROVIDER": "openrouter"}, clear=False):
                self.assertEqual(nebius.select_provider(), "nebius")

    def test_disconnected_keeps_openrouter_env(self) -> None:
        with patch.object(nebius, "is_connected", return_value=False):
            with patch.dict("os.environ", {"LLM_PROVIDER": "openrouter"}, clear=False):
                self.assertEqual(nebius.select_provider(), "openrouter")

    def test_nvidia_nim_env_wins_even_when_nebius_connected(self) -> None:
        with patch.object(nebius, "is_connected", return_value=True):
            with patch.dict("os.environ", {"LLM_PROVIDER": "nvidia_nim"}, clear=False):
                self.assertEqual(nebius.select_provider(), "nvidia_nim")

    def test_explicit_provider_wins(self) -> None:
        with patch.object(nebius, "is_connected", return_value=True):
            with patch.dict("os.environ", {"LLM_PROVIDER": "openrouter"}, clear=False):
                self.assertEqual(nebius.select_provider("openrouter"), "openrouter")

    def test_no_env_no_key_defaults_openrouter(self) -> None:
        with patch.object(nebius, "is_connected", return_value=False):
            with patch.dict("os.environ", {}, clear=False):
                # Ensure LLM_PROVIDER is absent for this assertion.
                env = {k: v for k, v in __import__("os").environ.items() if k != "LLM_PROVIDER"}
                with patch.dict("os.environ", env, clear=True):
                    self.assertEqual(nebius.select_provider(), "openrouter")


if __name__ == "__main__":
    unittest.main()
