"""WebVTT parsing for Teams / Zoom platform transcripts."""

from __future__ import annotations

import unittest

from app.services import vtt

TEAMS_VTT = """WEBVTT

0f6a1c2e-1/12-0
00:00:01.250 --> 00:00:04.000
<v Hon. Lady Justice Mwangi>Good morning. This matter is for mention.</v>

0f6a1c2e-1/18-0
00:00:04.500 --> 00:00:09.120
<v Jane Wanjiru>Your Ladyship, I appear for the plaintiff.</v>
"""

ZOOM_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:03.500
Peter Otieno: Mheshimiwa, naomba tarehe nyingine.

2
00:01:02.000 --> 00:01:05.000
Court Clerk: The matter is adjourned to 12th March 2025.
"""


class VttTests(unittest.TestCase):
    def test_teams_voice_tags(self) -> None:
        segs = vtt.parse(TEAMS_VTT)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0]["speaker"], "Hon. Lady Justice Mwangi")
        self.assertEqual(segs[0]["text"], "Good morning. This matter is for mention.")
        self.assertEqual(segs[0]["start_ms"], 1250)
        self.assertEqual(segs[1]["end_ms"], 9120)

    def test_zoom_speaker_prefix_and_kiswahili(self) -> None:
        segs = vtt.parse(ZOOM_VTT)
        self.assertEqual([s["speaker"] for s in segs], ["Peter Otieno", "Court Clerk"])
        self.assertEqual(segs[0]["text"], "Mheshimiwa, naomba tarehe nyingine.")
        self.assertEqual(segs[1]["start_ms"], 62_000)

    def test_crlf_bom_and_note_blocks(self) -> None:
        raw = "﻿WEBVTT\r\n\r\nNOTE generated\r\n\r\n00:05.000 --> 00:06.000\r\nHello court\r\n"
        segs = vtt.parse(raw)
        self.assertEqual(len(segs), 1)
        self.assertIsNone(segs[0]["speaker"])
        self.assertEqual(segs[0]["start_ms"], 5000)

    def test_colon_in_prose_is_not_a_speaker(self) -> None:
        segs = vtt.parse("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nnote: lowercase label stays text\n")
        self.assertIsNone(segs[0]["speaker"])

    def test_empty_input(self) -> None:
        self.assertEqual(vtt.parse("WEBVTT\n"), [])


if __name__ == "__main__":
    unittest.main()
