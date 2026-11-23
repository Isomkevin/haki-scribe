"""Durable /process job queue: leases, retries, restart resume, claim races."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest import mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.schemas import Hearing, HearingSource, HearingStatus
from app.services import hearing_jobs, hearing_pipeline, hearings
from tests.fake_supabase import FakeSupabase
from tests.stage_b_helpers import IsolatedStoreTestCase


def _ready_hearing() -> Hearing:
    hearing = Hearing(
        source=HearingSource.manual_upload,
        title="Petition E45/2024 mention",
        status=HearingStatus.ingested,
        matter_id=uuid4(),
        recording_object_key="hearings/x/audio.wav",
    )
    hearings._hearings[hearing.id] = hearing
    return hearing


def _pipeline(hearing_id):
    return (hearings.get_hearing(hearing_id).platform_metadata or {}).get("pipeline") or {}


def _run(coro):
    return asyncio.run(coro)


class MemoryQueueTests(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.store = hearing_jobs.MemoryJobStore()
        self.calls: list = []

        async def fake_process(hearing_id, **kwargs):
            self.calls.append((hearing_id, kwargs))
            return {"hearing": hearings.get_hearing(hearing_id)}

        self.process = mock.patch.object(hearing_pipeline, "process_hearing", side_effect=fake_process)
        self.process.start()

    def tearDown(self) -> None:
        self.process.stop()
        super().tearDown()

    def test_enqueue_marks_pipeline_and_refuses_duplicates(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {"use_llm": False}, store=self.store)
        self.assertEqual(_pipeline(hearing.id)["state"], "queued")
        self.assertEqual(_pipeline(hearing.id)["job_id"], job["id"])
        with self.assertRaises(hearing_jobs.JobConflict):
            hearing_jobs.enqueue(hearing.id, {}, store=self.store)

    def test_drain_runs_job_to_done_with_its_params(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {"use_llm": False, "language_hint": "sw"}, store=self.store)
        self.assertEqual(_run(hearing_jobs.drain_once(store=self.store)), "done")
        self.assertEqual(self.store.get(job["id"])["status"], "done")
        self.assertEqual(self.calls[0][1]["language_hint"], "sw")
        self.assertFalse(self.calls[0][1]["use_llm"])
        # Finished jobs no longer block a re-process.
        hearing_jobs.enqueue(hearing.id, {}, store=self.store)

    def test_transient_failure_is_retried_then_succeeds(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        attempts = {"n": 0}

        async def flaky(hearing_id, **kwargs):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise ConnectionError("whisper unreachable")
            return {"hearing": hearings.get_hearing(hearing_id)}

        with mock.patch.object(hearing_pipeline, "process_hearing", side_effect=flaky):
            self.assertEqual(_run(hearing_jobs.drain_once(store=self.store)), "queued")
            pipeline = _pipeline(hearing.id)
            self.assertEqual(pipeline["state"], "queued")
            self.assertIn("Attempt 1 of 3 failed", pipeline["error"])
            self.assertEqual(_run(hearing_jobs.drain_once(store=self.store)), "done")
        row = self.store.get(job["id"])
        self.assertEqual((row["status"], row["attempts"]), ("done", 2))

    def test_pipeline_error_is_not_retried(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        with mock.patch.object(
            hearing_pipeline, "process_hearing", side_effect=hearing_pipeline.PipelineError("no speech")
        ):
            self.assertEqual(_run(hearing_jobs.drain_once(store=self.store)), "error")
        row = self.store.get(job["id"])
        self.assertEqual((row["status"], row["attempts"], row["last_error"]), ("error", 1, "no speech"))
        self.assertIsNone(_run(hearing_jobs.drain_once(store=self.store)))

    def test_dead_worker_lease_expires_and_another_worker_takes_over(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        claimed = hearing_jobs.claim_next("worker-a", store=self.store)
        self.assertEqual(claimed["worker_id"], "worker-a")
        # worker-a dies without finishing: nobody can claim until the lease lapses.
        self.assertIsNone(hearing_jobs.claim_next("worker-b", store=self.store))
        hearings._jobs[job["id"]]["lease_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        retaken = hearing_jobs.claim_next("worker-b", store=self.store)
        self.assertEqual((retaken["worker_id"], retaken["attempts"]), ("worker-b", 2))
        # worker-a coming back cannot overwrite worker-b's outcome.
        self.assertFalse(self.store.finish(job["id"], "worker-a", "done"))
        self.assertFalse(self.store.heartbeat(job["id"], "worker-a"))

    def test_job_gives_up_after_max_attempts_of_dead_workers(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        for n in range(3):
            self.assertIsNotNone(hearing_jobs.claim_next(f"w{n}", store=self.store))
            hearings._jobs[job["id"]]["lease_expires_at"] = past
        self.assertIsNone(hearing_jobs.claim_next("w-last", store=self.store))
        self.assertEqual(self.store.get(job["id"])["status"], "error")
        self.assertEqual(_pipeline(hearing.id)["state"], "error")
        self.assertIn("Gave up after 3 attempts", _pipeline(hearing.id)["error"])

    def test_restart_resumes_running_job_instead_of_failing_it(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        hearing_jobs.claim_next("dead-process", store=self.store)
        hearings.set_pipeline_state(hearing.id, state="running", step="transcribe")
        payload = hearings.snapshot()

        hearings.restore(payload)  # what a fresh process does on boot

        self.assertEqual(self.store.get(job["id"])["status"], "queued")
        self.assertEqual(_pipeline(hearing.id)["state"], "queued")
        self.assertEqual(_pipeline(hearing.id)["step"], "resuming")
        self.assertEqual(_run(hearing_jobs.drain_once(store=self.store)), "done")
        self.assertEqual(self.store.get(job["id"])["attempts"], 2)

    def test_lost_lease_cancels_the_run(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=self.store)
        started = {}

        async def slow(hearing_id, **kwargs):
            started["yes"] = True
            # Another worker steals the job while this run is in progress.
            hearings._jobs[job["id"]]["worker_id"] = "thief"
            await asyncio.sleep(10)

        with mock.patch.dict(os.environ, {"HAKISCRIBE_JOB_HEARTBEAT_S": "1", "HAKISCRIBE_JOB_LEASE_S": "3"}), \
                mock.patch.object(hearing_pipeline, "process_hearing", side_effect=slow):
            result = _run(asyncio.wait_for(hearing_jobs.drain_once(store=self.store), timeout=5))
        self.assertTrue(started)
        self.assertEqual(result, "lost")


class DemoRouteTests(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        from app.main import app

        self.client = TestClient(app)

    def test_process_route_queues_job_and_refuses_while_active(self):
        hearing = _ready_hearing()
        hearing_jobs.enqueue(hearing.id, {}, store=hearing_jobs.MemoryJobStore())
        r = self.client.post(f"/hearings/{hearing.id}/process")
        self.assertEqual(r.status_code, 409)
        r = self.client.post(f"/hearings/{hearing.id}/process?wait=true")
        self.assertEqual(r.status_code, 409)

    def test_process_route_rejects_unprocessable_hearing_up_front(self):
        hearing = _ready_hearing()
        hearing.recording_object_key = None
        r = self.client.post(f"/hearings/{hearing.id}/process")
        self.assertEqual(r.status_code, 409)
        self.assertIn("No recording", r.json()["detail"])
        self.assertEqual(hearings._jobs, {})

    def test_process_route_returns_job_and_drains_in_process_without_worker(self):
        hearing = _ready_hearing()

        async def fake_process(hearing_id, **kwargs):
            return {"hearing": hearings.get_hearing(hearing_id)}

        with mock.patch.dict(os.environ, {"HAKISCRIBE_AI_MODE": "local_only"}), \
                mock.patch.object(hearing_pipeline, "process_hearing", side_effect=fake_process):
            r = self.client.post(f"/hearings/{hearing.id}/process")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "queued")
        self.assertIsNone(body["run_id"])
        self.assertEqual(hearings._jobs[body["job_id"]]["status"], "done")


class InternalRelayTests(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        from app.main import app
        from app.routers import internal

        self.client = TestClient(app)
        self.secret = mock.patch.object(internal, "INTERNAL_SECRET", "s3cret")
        self.secret.start()

    def tearDown(self) -> None:
        self.secret.stop()
        super().tearDown()

    def test_relay_claims_job_by_id_and_ignores_already_claimed(self):
        hearing = _ready_hearing()
        job = hearing_jobs.enqueue(hearing.id, {}, store=hearing_jobs.MemoryJobStore())

        async def fake_process(hearing_id, **kwargs):
            return {"hearing": hearings.get_hearing(hearing_id)}

        headers = {"X-Internal-Secret": "s3cret"}
        with mock.patch.object(hearing_pipeline, "process_hearing", side_effect=fake_process):
            first = self.client.post("/internal/process-hearing", json={"job_id": job["id"]}, headers=headers)
            again = self.client.post("/internal/process-hearing", json={"job_id": job["id"]}, headers=headers)
        self.assertEqual(first.json()["status"], "done")
        self.assertEqual(again.json()["status"], "not_claimed")

    def test_relay_requires_job_id_and_secret(self):
        self.assertEqual(
            self.client.post("/internal/process-hearing", json={"hearing_id": str(uuid4())}, headers={"X-Internal-Secret": "s3cret"}).status_code,
            400,
        )
        self.assertEqual(self.client.post("/internal/process-hearing", json={"job_id": "x"}).status_code, 401)

    def test_production_without_secret_fails_closed(self):
        from app.routers import internal

        with mock.patch.object(internal, "INTERNAL_SECRET", ""), \
                mock.patch.dict(os.environ, {"HAKISCRIBE_PRODUCTION_AUTH": "true"}):
            r = self.client.post("/internal/process-hearing", json={"job_id": "x"})
        self.assertEqual(r.status_code, 503)


class ProductionPipelineThroughQueueTests(IsolatedStoreTestCase):
    """Real pipeline (VTT path, rules only) against the org-scoped repo, via a job."""

    VTT = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Hon. Justice Odhiambo>"
        "Matter adjourned to 12th March 2025 for hearing.</v>\n"
    )

    def test_queued_production_job_writes_org_scoped_session_and_record(self):
        from app.models.schemas import HearingConfirmRequest, HearingCreate
        from app.services.production_hearings import ProductionHearingsRepo

        db = FakeSupabase()
        org, workspace, user = uuid4(), uuid4(), str(uuid4())
        matter = uuid4()
        db.tables["haki_matters"] = [
            {"id": str(matter), "organisation_id": str(org), "client_name": "Acme", "matter_name": "Acme v KPLC"}
        ]
        repo = ProductionHearingsRepo(db, org)
        hearing = repo.create(HearingCreate(source=HearingSource.manual_upload, title="Acme v KPLC mention"))
        repo.confirm_match(hearing.id, HearingConfirmRequest(decision="confirm", matter_id=matter), actor="a@b.ke")
        hearing_pipeline.ingest_transcript(hearing.id, self.VTT, origin="upload", store=repo)

        store = hearing_jobs.SupabaseJobStore(db)
        with mock.patch("app.services.tenant_context.production_client", return_value=db):
            job = hearing_jobs.enqueue(
                hearing.id, {"use_llm": False}, store=store, hearing_store=repo,
                organisation_id=org, workspace_id=workspace, user_id=user,
            )
            self.assertEqual(_run(hearing_jobs.drain_once(store=store)), "done")
            # Re-processing replaces the transcript instead of appending to it.
            hearing_jobs.enqueue(
                hearing.id, {"use_llm": False}, store=store, hearing_store=repo,
                organisation_id=org, workspace_id=workspace, user_id=user,
            )
            self.assertEqual(_run(hearing_jobs.drain_once(store=store)), "done")

        done = repo.get_hearing(hearing.id)
        self.assertEqual(done.status, HearingStatus.transcribed)
        self.assertEqual(done.platform_metadata["pipeline"]["state"], "done")
        self.assertEqual(store.get(job["id"])["status"], "done")
        sessions = db.tables["haki_sessions"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(
            (sessions[0]["organisation_id"], sessions[0]["workspace_id"], sessions[0]["created_by"], sessions[0]["matter_id"]),
            (str(org), str(workspace), user, str(matter)),
        )
        segments = [r for r in db.tables["haki_session_records"] if r["record_type"] == "segment"]
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["payload"]["speaker"], "Hon. Justice Odhiambo")
        rules = done.platform_metadata["proceedings"]["rules"]
        self.assertTrue(any("2025-03-12" in str(item) for item in rules), rules)


class SupabaseQueueTests(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.db = FakeSupabase()
        self.store = hearing_jobs.SupabaseJobStore(self.db)

    def _job(self, hearing_id=None):
        return hearing_jobs.new_job(hearing_id or uuid4(), {}, organisation_id=uuid4(), workspace_id=uuid4(), user_id=str(uuid4()))

    def test_only_one_of_two_racing_workers_claims(self):
        job = self.store.insert(self._job())
        now = datetime.now(timezone.utc)
        # Both workers read the same queued row, then both try to claim it.
        a = self.store.claim(dict(job), "worker-a", now)
        b = self.store.claim(dict(job), "worker-b", now)
        self.assertIsNotNone(a)
        self.assertIsNone(b)
        self.assertEqual(self.store.get(job["id"])["worker_id"], "worker-a")

    def test_duplicate_active_job_is_a_conflict(self):
        hid = uuid4()
        self.store.insert(self._job(hid))
        with self.assertRaises(hearing_jobs.JobConflict):
            self.store.insert(self._job(hid))

    def test_expired_lease_reclaim_and_heartbeat_ownership(self):
        job = self.store.insert(self._job())
        claimed = hearing_jobs.claim_next("worker-a", store=self.store)
        self.assertTrue(self.store.heartbeat(job["id"], "worker-a"))
        self.assertIsNone(hearing_jobs.claim_next("worker-b", store=self.store))
        self.db.tables["haki_hearing_jobs"][0]["lease_expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=5)
        ).isoformat()
        retaken = hearing_jobs.claim_next("worker-b", store=self.store)
        self.assertEqual((retaken["worker_id"], retaken["attempts"]), ("worker-b", claimed["attempts"] + 1))
        self.assertFalse(self.store.heartbeat(job["id"], "worker-a"))
        self.assertTrue(self.store.finish(job["id"], "worker-b", "done"))
        self.assertIsNone(self.store.active_for(job["hearing_id"]))
