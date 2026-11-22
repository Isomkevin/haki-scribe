"""Hearing lifecycle, matter resolution edge cases, and recording storage."""

from __future__ import annotations

import os
import unittest
import uuid

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, HearingStatus, Matter
from app.services import hearing_pipeline, hearings, matter_resolution, recording_store, storage
from tests.stage_b_helpers import IsolatedStoreTestCase


class CaseReferenceTests(unittest.TestCase):
    def test_canonical_refs(self) -> None:
        c = matter_resolution.canonical_case_refs
        self.assertEqual(c("HCCC No. E045 of 2024"), {"E45/2024"})
        self.assertEqual(c("ELRC Cause No. E45/2024"), {"E45/2024"})
        self.assertEqual(c("Civil Suit No. 45 of 2023"), {"45/2023"})
        self.assertEqual(c("Wanjiku v Acme"), set())

    def test_short_reference_does_not_match_longer_number(self) -> None:
        matter = matter_resolution.Matter(client_name="Zed", matter_name="Petition 120/2023")
        score, rationale = matter_resolution.score_matter(matter, title="Mention", case_reference="12")
        self.assertLess(score, 0.3, rationale)

    def test_same_client_different_suit_is_penalised(self) -> None:
        right = Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024 lease")
        wrong = Matter(client_name="Acme Holdings", matter_name="HCCC E200 of 2023 debt")
        cands = matter_resolution.propose_matches(
            [wrong, right], title="Acme Holdings — HCCC No. E123 of 2024 hearing"
        )
        self.assertEqual(cands[0]["matter_id"], str(right.id))
        wrong_row = next(c for c in cands if c["matter_id"] == str(wrong.id))
        self.assertIn("conflict", wrong_row["rationale"])
        self.assertGreater(cands[0]["score"] - wrong_row["score"], matter_resolution.AMBIGUITY_MARGIN)

    def test_near_tie_is_ambiguous(self) -> None:
        a = Matter(client_name="Acme Holdings", matter_name="Lease dispute")
        b = Matter(client_name="Acme Holdings", matter_name="Debt recovery")
        cands = matter_resolution.propose_matches([a, b], title="Acme Holdings hearing")
        self.assertTrue(matter_resolution.is_ambiguous(cands))
        self.assertIsNone(matter_resolution.best_match(cands))


class HearingLifecycleTests(IsolatedStoreTestCase):
    def _matter(self, client="Acme Holdings", name="HCCC E123 of 2024 lease") -> Matter:
        return storage.create_matter(Matter(client_name=client, matter_name=name))

    def _hearing(self, external_id="evt-1", title="Acme Holdings HCCC No. E123 of 2024 mention"):
        return hearings.upsert_external(
            HearingCreate(source=HearingSource.google_calendar, external_id=external_id, title=title)
        )

    def test_reimport_preserves_confirmation(self) -> None:
        matter = self._matter()
        h = self._hearing()
        hearings.propose_matches(h.id)
        self.assertEqual(h.status, HearingStatus.pending_confirm)
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))

        again = self._hearing()  # calendar re-import of the same event
        hearings.propose_matches(again.id)
        self.assertEqual(again.id, h.id)
        self.assertEqual(again.status, HearingStatus.matched)
        self.assertEqual(again.matter_id, matter.id)

    def test_reimport_preserves_rejection(self) -> None:
        self._matter()
        h = self._hearing()
        hearings.propose_matches(h.id)
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="reject"))
        hearings.propose_matches(self._hearing().id)
        self.assertEqual(h.status, HearingStatus.rejected)

    def test_high_confidence_still_needs_human(self) -> None:
        self._matter()
        h = self._hearing()
        cands = hearings.propose_matches(h.id)
        self.assertGreaterEqual(cands[0].score, matter_resolution.AUTO_MATCH_THRESHOLD)
        self.assertIsNone(h.matter_id)
        self.assertEqual(h.status, HearingStatus.pending_confirm)

    def test_illegal_transition_rejected(self) -> None:
        h = self._hearing()
        with self.assertRaises(hearings.InvalidTransition):
            hearings.transition(h, HearingStatus.filed)
        with self.assertRaises(hearings.InvalidTransition):
            hearings.mark_reviewed(h.id)

    def test_recording_before_confirm_waits_then_ingests(self) -> None:
        matter = self._matter()
        h = self._hearing()
        hearings.propose_matches(h.id)
        hearing_pipeline.ingest_recording(h.id, "hearing.wav", b"RIFF....", "audio/wav")
        self.assertEqual(h.status, HearingStatus.pending_confirm)
        self.assertTrue(h.recording_object_key)
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        self.assertEqual(h.status, HearingStatus.ingested)

    def test_matter_link_locked_after_capture(self) -> None:
        matter = self._matter()
        h = self._hearing()
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        hearings.create_session_from_hearing(h.id)
        self.assertEqual(h.status, HearingStatus.capturing)
        with self.assertRaises(hearings.InvalidTransition):
            hearings.confirm_match(h.id, HearingConfirmRequest(decision="reject"))

    def test_session_creation_is_idempotent(self) -> None:
        matter = self._matter()
        h = self._hearing()
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        first = hearings.create_session_from_hearing(h.id)["session"]
        second = hearings.create_session_from_hearing(h.id)["session"]
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(storage.list_sessions()), 1)


class RecordingStoreTests(IsolatedStoreTestCase):
    def test_traversal_names_are_sanitised(self) -> None:
        hid = uuid.uuid4()
        stored = recording_store.save(hid, "../../etc/passwd", b"x")
        self.assertEqual(stored["key"], f"hearings/{hid}/passwd")
        stored = recording_store.save(hid, "..\\..\\win.ini", b"x")
        self.assertEqual(stored["key"], f"hearings/{hid}/win.ini")
        self.assertTrue(str(recording_store._path_for(stored["key"])).startswith(os.path.realpath(self._tmp)))

    def test_round_trip_and_size_limit(self) -> None:
        hid = uuid.uuid4()
        stored = recording_store.save(hid, "a.wav", b"abc")
        self.assertEqual(recording_store.load(stored["key"]), b"abc")
        with unittest.mock.patch.dict(os.environ, {"HAKISCRIBE_MAX_RECORDING_MB": "0"}):
            with self.assertRaises(recording_store.RecordingTooLarge):
                recording_store.save(hid, "b.wav", b"abc")

    def test_key_outside_root_refused(self) -> None:
        with self.assertRaises(ValueError):
            recording_store.load("../outside.bin")


if __name__ == "__main__":
    unittest.main()
