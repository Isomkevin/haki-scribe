"""Proceedings extraction: EN/SW rules, quote grounding, LLM failure honesty."""

from __future__ import annotations

import asyncio
import json
import unittest
import uuid
from unittest import mock

from app.models.schemas import TranscriptSegment
from app.services import ai_mode, ai_runs, generation, proceedings_intel

SID = uuid.uuid4()


def seg(text: str, start: int, speaker: str | None = None, redacted: bool = False) -> TranscriptSegment:
    return TranscriptSegment(session_id=SID, text=text, start_ms=start, end_ms=start + 4000, speaker=speaker, redacted=redacted)


TRANSCRIPT = [
    seg("Good morning, this matter is coming up for hearing.", 0, "Court"),
    seg("Your Honour, the plaintiff's witness is unwell and we seek an adjournment.", 5000, "Counsel"),
    seg("The matter is adjourned to 12th March 2025 for hearing.", 10000, "Court"),
    seg("Shauri hili limeahirishwa, litatajwa tarehe 3 Aprili 2025.", 15000, "Karani"),
    seg("Privileged: client admitted the debt on 1st May 2024 hearing", 20000, "Counsel", redacted=True),
    seg("The witness was born on 4th July 1980.", 25000, "Counsel"),
]


class RulesTests(unittest.TestCase):
    def test_english_and_kiswahili_next_dates(self) -> None:
        found = proceedings_intel.extract_next_dates_rules(TRANSCRIPT)
        dates = {(f["date"], f["purpose"]) for f in found}
        self.assertIn(("2025-03-12", "hearing"), dates)
        self.assertIn(("2025-04-03", "mention"), dates)

    def test_privileged_and_uncued_dates_excluded(self) -> None:
        dates = {f["date"] for f in proceedings_intel.extract_next_dates_rules(TRANSCRIPT)}
        self.assertNotIn("2024-05-01", dates)  # redacted line
        self.assertNotIn("1980-07-04", dates)  # no court cue

    def test_numeric_day_first(self) -> None:
        found = proceedings_intel.extract_next_dates_rules([seg("Mention on 05/06/2025 before the DR.", 0)])
        self.assertEqual(found[0]["date"], "2025-06-05")


class GroundingTests(unittest.TestCase):
    def test_exact_quote_grounds_with_punctuation_and_case_drift(self) -> None:
        ref = proceedings_intel.ground_quote("the MATTER is adjourned to 12th March 2025", TRANSCRIPT)
        self.assertEqual(ref["start_ms"], 10000)

    def test_quote_spanning_two_segments(self) -> None:
        ref = proceedings_intel.ground_quote("seek an adjournment. The matter is adjourned", TRANSCRIPT)
        self.assertIsNotNone(ref)
        self.assertEqual(len(ref["spans_segments"]), 2)

    def test_fabricated_or_privileged_quote_rejected(self) -> None:
        self.assertIsNone(proceedings_intel.ground_quote("judgment entered for the plaintiff", TRANSCRIPT))
        self.assertIsNone(proceedings_intel.ground_quote("client admitted the debt", TRANSCRIPT))
        self.assertIsNone(proceedings_intel.ground_quote("hearing", TRANSCRIPT))  # too short

    def test_payload_split(self) -> None:
        payload = {
            "next_dates": [
                {"date": "2025-03-12", "purpose": "hearing", "quote": "The matter is adjourned to 12th March 2025 for hearing."},
                {"date": "next week", "purpose": "hearing", "quote": "The matter is adjourned to 12th March 2025 for hearing."},
            ],
            "orders": [{"text": "Costs to the defendant", "quote": "costs are awarded to the defendant"}],
        }
        grounded, ungrounded = proceedings_intel.ground_llm_payload(payload, TRANSCRIPT)
        self.assertEqual([g["kind"] for g in grounded], ["next_date"])
        reasons = sorted(u["reason"] for u in ungrounded)
        self.assertEqual(reasons, ["invalid date", "quote not found in transcript"])

    def test_schema_placeholders_rejected_even_with_real_quote(self) -> None:
        # Shape observed from qwen2.5:3b on the real local stack.
        quote = "The matter is adjourned to 12th March 2025 for hearing."
        payload = {
            "outcome": [{"text": "what happened at this sitting", "quote": quote}],
            "orders": [{"text": "<the order the court made>", "quote": quote}],
            "appearances": [{"name": "person", "role": "counsel", "quote": quote}],
        }
        grounded, ungrounded = proceedings_intel.ground_llm_payload(payload, TRANSCRIPT)
        self.assertEqual(grounded, [])
        self.assertEqual({u["reason"] for u in ungrounded}, {"model echoed the schema placeholder"})

    def test_copied_line_prefix_is_tolerated_but_remainder_must_match(self) -> None:
        line = "The matter is adjourned to 12th March 2025 for hearing."
        for quote in (f"Court: {line}", f"[1] (00:10) Hon. Justice Odhiambo: {line}"):
            ref = proceedings_intel._ground_with_prefix_tolerance(quote, TRANSCRIPT)
            self.assertIsNotNone(ref, quote)
            self.assertEqual(ref["start_ms"], 10000)
        self.assertIsNone(
            proceedings_intel._ground_with_prefix_tolerance("Court: judgment entered for the plaintiff", TRANSCRIPT)
        )


class ExtractTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_mode.clear_runtime_overrides()
        ai_runs.clear()

    def tearDown(self) -> None:
        ai_mode.clear_runtime_overrides()

    def test_llm_output_grounded_and_logged(self) -> None:
        reply = json.dumps(
            {
                "outcome": [{"text": "Adjourned", "quote": "The matter is adjourned to 12th March 2025"}],
                "appearances": [{"name": "Invented Person", "role": "counsel", "quote": "I appear for the state"}],
            }
        )

        async def fake_complete(*args, **kwargs):
            generation._last_completion = {"provider": "Ollama (local)", "model": "test-model"}
            return f"```json\n{reply}\n```"

        with mock.patch.object(generation, "complete_text", fake_complete):
            result = asyncio.run(proceedings_intel.extract(TRANSCRIPT))
        self.assertEqual(result["llm"]["status"], "ok")
        self.assertEqual(len(result["llm"]["items"]), 1)
        self.assertEqual(len(result["llm"]["ungrounded"]), 1)
        self.assertEqual(result["privileged_segments_excluded"], 1)
        self.assertEqual(ai_runs.recent(1)[0]["task"], "proceedings")

    def test_llm_prompt_never_contains_privileged_text(self) -> None:
        seen: list[str] = []

        async def capture(system, user, provider=None, *, task="draft"):
            seen.append(user)
            return "{}"

        with mock.patch.object(generation, "complete_text", capture):
            asyncio.run(proceedings_intel.extract(TRANSCRIPT))
        self.assertNotIn("client admitted the debt", seen[0])

    def test_llm_failure_keeps_rules_and_reports_error(self) -> None:
        async def boom(*args, **kwargs):
            raise RuntimeError("connection refused")

        generation._last_completion = {"provider": "OpenRouter", "model": "stale"}
        with mock.patch.object(generation, "complete_text", boom):
            result = asyncio.run(proceedings_intel.extract(TRANSCRIPT))
        self.assertEqual(result["llm"]["status"], "error")
        self.assertIsNone(result["llm"]["provider"])  # no stale provenance
        self.assertTrue(result["rules"])

    def test_local_only_blocks_cloud_provider(self) -> None:
        ai_mode.set_runtime_config(mode="local_only")
        result = asyncio.run(proceedings_intel.extract(TRANSCRIPT, provider="openrouter"))
        self.assertEqual(result["llm"]["status"], "blocked_by_ai_mode")


if __name__ == "__main__":
    unittest.main()
