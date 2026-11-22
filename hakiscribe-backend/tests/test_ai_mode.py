"""AI mode + hybrid routing + frontier preservation."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from app.services import ai_mode


class AiModeTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_mode.clear_runtime_overrides()
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("HAKISCRIBE_AI_MODE", None)
        for key in ai_mode.ROUTE_ENV.values():
            os.environ.pop(key, None)
        os.environ.pop("HAKISCRIBE_HYBRID_FALLBACK", None)

    def tearDown(self) -> None:
        ai_mode.clear_runtime_overrides()
        self._env.stop()

    def test_default_mode_is_cloud(self) -> None:
        self.assertEqual(ai_mode.get_mode(), "cloud")
        snap = ai_mode.snapshot()
        self.assertTrue(snap["frontier_preserved"])

    def test_local_only_blocks_public_cloud(self) -> None:
        os.environ["HAKISCRIBE_AI_MODE"] = "local_only"
        self.assertFalse(ai_mode.is_provider_allowed("detect", "nebius"))
        self.assertFalse(ai_mode.is_provider_allowed("draft", "anthropic"))
        self.assertFalse(ai_mode.is_provider_allowed("asr", "openrouter"))
        self.assertTrue(ai_mode.is_provider_allowed("asr", "local_whisper"))
        self.assertTrue(ai_mode.is_provider_allowed("detect", "ollama"))
        self.assertTrue(ai_mode.is_provider_allowed("research", "off"))
        with self.assertRaises(ai_mode.AiModeError):
            ai_mode.assert_provider_allowed("draft", "openai")

    def test_cloud_allows_frontier(self) -> None:
        os.environ["HAKISCRIBE_AI_MODE"] = "cloud"
        for provider in ("anthropic", "openai", "nebius", "openrouter", "gemini", "groq"):
            self.assertTrue(ai_mode.is_provider_allowed("ask", provider), provider)

    def test_hybrid_independent_routes(self) -> None:
        os.environ["HAKISCRIBE_AI_MODE"] = "hybrid"
        os.environ["HAKISCRIBE_ROUTE_ASR"] = "local_whisper"
        os.environ["HAKISCRIBE_ROUTE_DRAFT"] = "anthropic"
        os.environ["HAKISCRIBE_ROUTE_DETECT"] = "nebius"
        self.assertEqual(ai_mode.get_route("asr"), "local_whisper")
        self.assertEqual(ai_mode.get_route("draft"), "anthropic")
        self.assertEqual(ai_mode.get_route("detect"), "nebius")
        self.assertTrue(ai_mode.is_provider_allowed("asr", "local_whisper"))
        self.assertTrue(ai_mode.is_provider_allowed("draft", "anthropic"))
        self.assertTrue(ai_mode.snapshot()["frontier_preserved"])

    def test_private_blocks_public_saas(self) -> None:
        os.environ["HAKISCRIBE_AI_MODE"] = "private"
        self.assertFalse(ai_mode.is_provider_allowed("detect", "openrouter"))
        self.assertTrue(ai_mode.is_provider_allowed("detect", "nvidia_nim"))
        self.assertTrue(ai_mode.is_provider_allowed("detect", "ollama"))

    def test_runtime_override_reversible(self) -> None:
        ai_mode.set_runtime_config(mode="local_only")
        self.assertEqual(ai_mode.get_mode(), "local_only")
        ai_mode.set_runtime_config(mode="cloud")
        self.assertEqual(ai_mode.get_mode(), "cloud")
        self.assertTrue(ai_mode.is_provider_allowed("ask", "anthropic"))

    def test_prefer_in_process_only_local_only(self) -> None:
        os.environ["HAKISCRIBE_AI_MODE"] = "cloud"
        self.assertFalse(ai_mode.prefer_in_process_jobs())
        os.environ["HAKISCRIBE_AI_MODE"] = "local_only"
        self.assertTrue(ai_mode.prefer_in_process_jobs())


if __name__ == "__main__":
    unittest.main()
