"""Hearings survive a restart (ADR-012 option a) and background /process runs."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, HearingStatus, Matter
from app.routers import hearings as hearings_router
from app.services import hearings, storage
from tests.stage_b_helpers import IsolatedStoreTestCase

VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Hon. Justice Odhiambo>Matter adjourned to 12th March 2025 for hearing.</v>\n"


class HearingPersistenceTests(IsolatedStoreTestCase):
    def _restart(self) -> None:
        """Serialise the full workspace snapshot, wipe memory, load it back."""
        payload = json.loads(json.dumps(storage._snapshot(), default=str))
        hearings.reset()
        storage._restore(payload)
        hearings.restore(storage.take_hearings_payload())

    def test_confirmed_hearing_survives_restart(self) -> None:
        matter = storage.create_matter(Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024"))
        h = hearings.create_hearing(
            HearingCreate(source=HearingSource.zoom, external_id="z-1", title="Acme Holdings E123 of 2024")
        )
        hearings.propose_matches(h.id)
        hearings.confirm_match(h.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        session_id = hearings.create_session_from_hearing(h.id)["session"].id

        self._restart()

        restored = hearings.get_hearing(h.id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.status, HearingStatus.capturing)
        self.assertEqual(restored.matter_id, matter.id)
        self.assertEqual(restored.session_id, session_id)
        self.assertEqual(len(hearings.list_candidates(h.id)), 1)
        self.assertEqual(hearings.list_confirmations(h.id)[0]["decision"], "confirm")
        # Re-import after restart still finds the same hearing and keeps the confirmation.
        again = hearings.upsert_external(HearingCreate(source=HearingSource.zoom, external_id="z-1", title="renamed"))
        self.assertEqual(again.id, h.id)
        self.assertEqual(again.matter_id, matter.id)

    def test_in_flight_pipeline_marked_interrupted(self) -> None:
        h = hearings.create_hearing(HearingCreate(source=HearingSource.manual_upload, title="t"))
        hearings.set_pipeline_state(h.id, state="running", step="transcribe")

        self._restart()

        pipeline = hearings.get_hearing(h.id).platform_metadata["pipeline"]
        self.assertEqual(pipeline["state"], "error")
        self.assertIn("restart", pipeline["error"])

    def test_every_mutation_persists(self) -> None:
        calls = []
        storage._persist = lambda: calls.append(1)  # restored by IsolatedStoreTestCase's patch
        h = hearings.create_hearing(HearingCreate(source=HearingSource.manual_upload, title="t"))
        self.assertTrue(calls)
        calls.clear()
        hearings.set_pipeline_state(h.id, state="queued")
        self.assertTrue(calls)


class BackgroundProcessTests(IsolatedStoreTestCase):
    def test_background_process_completes(self) -> None:
        app = FastAPI()
        app.include_router(hearings_router.router, prefix="/hearings")
        client = TestClient(app)
        matter = storage.create_matter(Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024"))
        hid = client.post("/hearings/import/manual", json={"title": "Acme Holdings E123 of 2024"}).json()["hearing"]["id"]
        client.post(f"/hearings/{hid}/transcript", files={"file": ("t.vtt", VTT.encode(), "text/vtt")})
        client.post(f"/hearings/{hid}/confirm", json={"decision": "confirm", "matter_id": str(matter.id)})

        queued = client.post(f"/hearings/{hid}/process", params={"use_llm": "false"})
        self.assertEqual(queued.status_code, 200, queued.text)
        self.assertEqual(queued.json()["status"], "queued")

        # TestClient runs background tasks before returning; poll once as a client would.
        result = client.get(f"/hearings/{hid}/proceedings").json()
        self.assertEqual(result["pipeline"]["state"], "done", result["pipeline"])
        self.assertEqual(result["status"], "transcribed")
        dates = result["proceedings"]["rules"]
        self.assertTrue(any(d["date"] == "2025-03-12" for d in dates), dates)
