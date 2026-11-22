"""Cross-realm fallback policy, ai_runs logging, and local model health."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from app.services import ai_mode, ai_runs, inference_health


class FallbackPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_mode.clear_runtime_overrides()
        ai_runs.clear()

    def tearDown(self) -> None:
        ai_mode.clear_runtime_overrides()

    def test_matrix(self) -> None:
        cases = [
            ("cloud", "", True),
            ("hybrid", "", False),
            ("hybrid", "explicit_allow", True),
            ("private", "explicit_allow", False),
            ("local_only", "explicit_allow", False),
        ]
        for mode, fallback, expected in cases:
            with self.subTest(mode=mode, fallback=fallback):
                ai_mode.set_runtime_config(mode=mode)
                with mock.patch.dict(os.environ, {"HAKISCRIBE_HYBRID_FALLBACK": fallback}):
                    self.assertEqual(ai_mode.cloud_fallback_allowed("draft"), expected)

    def test_fallback_is_logged(self) -> None:
        ai_mode.record_fallback("draft", "nvidia_nim", "openrouter")
        row = ai_runs.recent(1)[0]
        self.assertEqual(row["provider"], "openrouter")
        self.assertEqual(row["status"], "fallback_from:nvidia_nim")


class OllamaHealthTests(unittest.TestCase):
    def test_model_presence_handles_latest_tag(self) -> None:
        self.assertTrue(inference_health._model_present("gemma4", ["gemma4:latest"]))
        self.assertTrue(inference_health._model_present("gemma4:latest", ["gemma4:latest"]))
        self.assertFalse(inference_health._model_present("llama3.1", ["gemma4:latest"]))
        self.assertFalse(inference_health._model_present("llama3.1:8b", ["llama3.1:70b"]))

    def test_route_warnings(self) -> None:
        snap = {"routes": {"asr": "local_whisper", "detect": "ollama", "draft": "anthropic"},
                "routes_allowed": {"asr": True, "detect": True, "draft": False}}
        probes = {"local_whisper": {"ok": True}, "ollama": {"ok": False, "detail": "model 'x' not pulled"}}
        warnings = inference_health.validate_routes(snap, probes)
        self.assertEqual({(w["task"], w["provider"]) for w in warnings}, {("detect", "ollama"), ("draft", "anthropic")})


if __name__ == "__main__":
    unittest.main()
