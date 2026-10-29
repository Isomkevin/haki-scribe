"""Short live Nemotron demo: privilege locked, no pre-seeded actions."""

from __future__ import annotations

import unittest

from app.services.live_nemotron_demo import LIVE_NEMOTRON_TITLE, live_nemotron_spec


class LiveNemotronDemoSpecTests(unittest.TestCase):
    def test_short_transcript_and_privilege(self) -> None:
        spec = live_nemotron_spec()
        self.assertEqual(spec["title"], LIVE_NEMOTRON_TITLE)
        self.assertFalse(spec.get("generate"))
        segments = spec["segments"]
        self.assertGreaterEqual(len(segments), 12)
        self.assertLessEqual(len(segments), 25)
        texts = " ".join(seg["text"] for seg in segments)
        self.assertIn("demand", texts.lower())
        self.assertIn("tax", texts.lower())
        self.assertTrue(spec.get("redact_indexes"))
        for index in spec["redact_indexes"]:
            self.assertIn("tax", segments[index]["text"].lower())
        # Working-session padding must never appear here.
        self.assertNotIn("Working session note", texts)

    def test_speakers_named(self) -> None:
        spec = live_nemotron_spec()
        speakers = spec["speakers"]
        self.assertIn("Speaker 1", speakers)
        self.assertIn("Speaker 2", speakers)
        self.assertIn("Naomi", speakers["Speaker 1"])
        self.assertIn("Wanjiru", speakers["Speaker 2"])


if __name__ == "__main__":
    unittest.main()
