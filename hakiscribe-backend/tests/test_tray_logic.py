"""Unit tests for privilege-aware tray helpers."""

from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace

from app.services import tray_logic


def _seg(text: str, *, redacted: bool = False, speaker: str = "Speaker") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), speaker=speaker, text=text, redacted=redacted)


class TrayLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s1 = _seg("Tell me about the lease.", speaker="Advocate")
        self.s2 = _seg("He stopped paying in March. Niliandika demand letter.", speaker="Client")
        self.s3 = _seg("Off record: I forged the second signature ZEBRA-PRIVILEGED-7731.", redacted=True, speaker="Client")
        self.s4 = _seg("Mention at Milimani on 12 November.", speaker="Advocate")
        self.segments = [self.s1, self.s2, self.s3, self.s4]

    def test_privileged_lines_absent_from_built_prompt(self) -> None:
        block = tray_logic.build_transcript_block(self.segments)
        self.assertNotIn("forged", block)
        self.assertNotIn("ZEBRA-PRIVILEGED-7731", block)
        self.assertIn("Niliandika", block)
        self.assertEqual(tray_logic.privileged_count(self.segments), 1)

    def test_actions_citing_only_privileged_or_nonexistent_dropped(self) -> None:
        raw = [
            {"type": "private_note", "title": "Forgery", "source_quote": "forged the second", "confidence": 0.9},
            {"type": "private_note", "title": "Ghost", "source_quote": "this quote does not exist", "confidence": 0.9},
            {
                "type": "calendar_event",
                "title": "Mention 12 Nov",
                "source_quote": "Milimani on 12 November",
                "confidence": 0.95,
            },
        ]
        kept, dropped = tray_logic.validate_raw_actions(raw, self.segments)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["title"], "Mention 12 Nov")
        self.assertEqual(len(dropped), 2)

    def test_duplicate_and_confidence_clamp(self) -> None:
        raw = [
            {"type": "email_blast", "title": "x", "source_quote": "lease"},
            {"type": "private_note", "title": "  ", "source_quote": "lease"},
            {"type": "private_note", "title": "Note", "source_quote": "lease", "confidence": 7},
            {"type": "private_note", "title": "note", "source_quote": "lease"},
        ]
        kept, dropped = tray_logic.validate_raw_actions(raw, self.segments)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["confidence"], 1.0)
        self.assertTrue(kept[0]["pre_checked"])
        self.assertEqual(len(dropped), 3)

    def test_extract_json_with_think_and_fences(self) -> None:
        self.assertEqual(
            tray_logic.extract_json('<think>hmm {"a":0}</think>\n```json\n{"a":1}\n```'),
            {"a": 1},
        )
        self.assertEqual(tray_logic.extract_json('Sure! {"a":2} done'), {"a": 2})
        with self.assertRaises(ValueError):
            tray_logic.extract_json("no json here")


if __name__ == "__main__":
    unittest.main()
