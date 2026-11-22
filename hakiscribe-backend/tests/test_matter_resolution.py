"""Matter resolution confidence + confirmation rules."""

from __future__ import annotations

import unittest
import uuid

from app.models.schemas import Matter
from app.services import matter_resolution


class MatterResolutionTests(unittest.TestCase):
    def test_extract_case_reference(self) -> None:
        ref = matter_resolution.extract_case_reference("Hearing Cause No. 123/2024 at Milimani")
        self.assertIsNotNone(ref)
        self.assertIn("123", ref or "")

    def test_strong_match_scores_high(self) -> None:
        matter = Matter(client_name="Acme Holdings", matter_name="Cause 123/2024 lease dispute")
        score, rationale = matter_resolution.score_matter(
            matter,
            title="Virtual hearing — Acme Holdings Cause 123/2024",
            description="Mention before Justice X",
            case_reference="123/2024",
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertIn("case reference", rationale.lower())

    def test_weak_match_requires_confirmation(self) -> None:
        matter = Matter(client_name="Other Client", matter_name="Unrelated file")
        candidates = matter_resolution.propose_matches(
            [matter],
            title="Mention — unknown parties",
            description="No identifiers",
        )
        self.assertTrue(matter_resolution.requires_human_confirmation(candidates))
        self.assertIsNone(matter_resolution.best_match(candidates))

    def test_propose_sorted_by_score(self) -> None:
        strong = Matter(
            id=uuid.uuid4(),
            client_name="Wanjiku",
            matter_name="Petition 9/2023",
        )
        weak = Matter(id=uuid.uuid4(), client_name="Someone Else", matter_name="Misc")
        candidates = matter_resolution.propose_matches(
            [weak, strong],
            title="Hearing Petition 9/2023 Wanjiku",
            case_reference="9/2023",
        )
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["matter_id"], str(strong.id))


if __name__ == "__main__":
    unittest.main()
