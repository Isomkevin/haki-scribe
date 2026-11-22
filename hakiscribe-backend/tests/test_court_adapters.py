"""Zoom / Teams recording flows against mocked platform APIs + Zoom webhook.

These are contract tests: request paths, auth headers and response shapes
follow the Zoom Cloud Recording and Microsoft Graph onlineMeeting docs. They
are NOT a substitute for a run against real sandbox tenants.
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, HearingStatus, Matter
from app.routers import court_webhooks, hearings as hearings_router
from app.services import hearings, integrations, storage
from app.services.court_adapters import AdapterError, TeamsGraphAdapter, ZoomAdapter, zoom_adapter
from tests.stage_b_helpers import IsolatedStoreTestCase

VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Hon. Justice Odhiambo>Matter adjourned to 12th March 2025 for hearing.</v>\n"


def _creds(_pid):
    return {"access_token": "user-token"}


async def _fresh(_pid):
    return {"access_token": "user-token"}


class AdapterTestCase(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        for p in (
            mock.patch.object(integrations, "get_creds", _creds),
            mock.patch.object(integrations, "get_fresh_creds", _fresh),
        ):
            p.start()
            self.addCleanup(p.stop)


class ZoomTests(AdapterTestCase):
    def test_pick_prefers_audio_then_transcript(self) -> None:
        files = [
            {"file_type": "MP4", "download_url": "u1", "status": "completed"},
            {"file_type": "M4A", "download_url": "u2", "status": "completed"},
            {"file_type": "TRANSCRIPT", "download_url": "u3", "status": "completed"},
            {"file_type": "M4A", "download_url": "u4", "status": "processing"},
        ]
        self.assertEqual(zoom_adapter.pick_recording_file(files)["download_url"], "u2")
        self.assertEqual(zoom_adapter.pick_recording_file(files, prefer="transcript")["download_url"], "u3")
        self.assertIsNone(zoom_adapter.pick_recording_file([files[3]]))

    def test_fetch_artifact_downloads_audio_with_bearer(self) -> None:
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.url.path, request.headers.get("authorization")))
            if request.url.path == "/v2/meetings/987654321/recordings":
                return httpx.Response(
                    200,
                    json={
                        "uuid": "abc==",
                        "recording_files": [
                            {"id": "f1", "file_type": "M4A", "file_extension": "M4A", "status": "completed",
                             "download_url": "https://zoom.us/rec/download/f1", "recording_type": "audio_only"},
                        ],
                    },
                )
            if request.url.path == "/rec/download/f1":
                return httpx.Response(200, content=b"m4a-bytes", headers={"content-type": "audio/mp4"})
            return httpx.Response(404)

        self.mock_http(handler)
        hearing = hearings.create_hearing(HearingCreate(source=HearingSource.zoom, external_id="987654321", title="t"))
        artifact = asyncio.run(ZoomAdapter().fetch_artifact(hearing))
        self.assertEqual(artifact.kind, "audio")
        self.assertEqual(artifact.data, b"m4a-bytes")
        self.assertTrue(all(auth == "Bearer user-token" for _, auth in seen))

    def test_no_recording_is_a_clear_error(self) -> None:
        self.mock_http(lambda r: httpx.Response(404, json={"code": 3301}))
        hearing = hearings.create_hearing(HearingCreate(source=HearingSource.zoom, external_id="1", title="t"))
        with self.assertRaisesRegex(AdapterError, "no cloud recording"):
            asyncio.run(ZoomAdapter().fetch_artifact(hearing))

    def test_signature(self) -> None:
        body = b'{"event":"recording.completed"}'
        ts = str(int(time.time()))
        sig = "v0=" + zoom_adapter.sign("s3cret", f"v0:{ts}:{body.decode()}")
        self.assertTrue(zoom_adapter.verify_webhook("s3cret", signature=sig, timestamp=ts, body=body))
        self.assertFalse(zoom_adapter.verify_webhook("other", signature=sig, timestamp=ts, body=body))
        self.assertFalse(zoom_adapter.verify_webhook("s3cret", signature=sig, timestamp=ts, body=body + b" "))
        old = str(int(time.time()) - 3600)
        old_sig = "v0=" + zoom_adapter.sign("s3cret", f"v0:{old}:{body.decode()}")
        self.assertFalse(zoom_adapter.verify_webhook("s3cret", signature=old_sig, timestamp=old, body=body))


class ZoomWebhookTests(AdapterTestCase):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        app.include_router(court_webhooks.router, prefix="/webhooks")
        self.client = TestClient(app)

    def _post(self, event: dict, secret="s3cret", sign=True):
        body = json.dumps(event).encode()
        ts = str(int(time.time()))
        headers = {"content-type": "application/json", "x-zm-request-timestamp": ts}
        if sign:
            headers["x-zm-signature"] = "v0=" + zoom_adapter.sign(secret, f"v0:{ts}:{body.decode()}")
        with mock.patch.dict("os.environ", {"ZOOM_WEBHOOK_SECRET_TOKEN": "s3cret"}):
            return self.client.post("/webhooks/zoom", content=body, headers=headers)

    def test_fails_closed_without_secret(self) -> None:
        with mock.patch.dict("os.environ", {"ZOOM_WEBHOOK_SECRET_TOKEN": ""}):
            resp = self.client.post("/webhooks/zoom", json={"event": "recording.completed"})
        self.assertEqual(resp.status_code, 503)

    def test_url_validation(self) -> None:
        resp = self._post({"event": "endpoint.url_validation", "payload": {"plainToken": "abc"}}, sign=False)
        self.assertEqual(resp.json()["encryptedToken"], zoom_adapter.sign("s3cret", "abc"))

    def test_bad_signature_rejected(self) -> None:
        resp = self._post({"event": "recording.completed", "payload": {}}, secret="wrong")
        self.assertEqual(resp.status_code, 401)

    def test_recording_completed_ingests_but_waits_for_confirm(self) -> None:
        storage.create_matter(Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024"))

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers.get("authorization"), "Bearer dl-token")
            return httpx.Response(200, content=b"audio", headers={"content-type": "audio/mp4"})

        self.mock_http(handler)
        event = {
            "event": "recording.completed",
            "download_token": "dl-token",
            "payload": {
                "object": {
                    "id": 555,
                    "uuid": "u==",
                    "topic": "Acme Holdings HCCC No. E123 of 2024 virtual hearing",
                    "start_time": "2025-03-01T07:00:00Z",
                    "recording_files": [
                        {"id": "a1", "file_type": "M4A", "file_extension": "M4A", "status": "completed",
                         "download_url": "https://zoom.us/rec/download/a1"}
                    ],
                }
            },
        }
        resp = self._post(event)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["ingest"], "queued")
        hearing = hearings.find_external(HearingSource.zoom, "555")
        self.assertIsNotNone(hearing.recording_object_key)
        self.assertEqual(hearing.status, HearingStatus.pending_confirm)  # human still decides
        self.assertIsNone(hearing.matter_id)


class TeamsTests(AdapterTestCase):
    JOIN = "https://teams.microsoft.com/l/meetup-join/19%3ameeting_x%40thread.v2/0"

    def _hearing(self):
        return hearings.create_hearing(
            HearingCreate(source=HearingSource.teams_graph, external_id="ev1", title="t", meeting_url=self.JOIN)
        )

    def test_transcript_preferred(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            path = request.url.path
            if path == "/v1.0/me/onlineMeetings":
                self.assertIn(self.JOIN, request.url.params["$filter"])
                return httpx.Response(200, json={"value": [{"id": "MSo1"}]})
            if path == "/v1.0/me/onlineMeetings/MSo1/transcripts":
                return httpx.Response(200, json={"value": [{"id": "t-old", "createdDateTime": "2025-01-01"},
                                                           {"id": "t-new", "createdDateTime": "2025-02-01"}]})
            if path == "/v1.0/me/onlineMeetings/MSo1/transcripts/t-new/content":
                self.assertEqual(request.url.params["$format"], "text/vtt")
                return httpx.Response(200, text=VTT)
            return httpx.Response(404)

        self.mock_http(handler)
        artifact = asyncio.run(TeamsGraphAdapter().fetch_artifact(self._hearing()))
        self.assertEqual(artifact.kind, "transcript")
        self.assertIn(b"Odhiambo", artifact.data)

    def test_transcript_forbidden_falls_back_to_recording(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/v1.0/me/onlineMeetings":
                return httpx.Response(200, json={"value": [{"id": "MSo1"}]})
            if path.endswith("/transcripts"):
                return httpx.Response(403, json={"error": {"code": "Forbidden"}})
            if path.endswith("/recordings"):
                return httpx.Response(200, json={"value": [{"id": "r1", "createdDateTime": "2025-02-01"}]})
            if path.endswith("/recordings/r1/content"):
                return httpx.Response(200, content=b"mp4", headers={"content-type": "video/mp4"})
            return httpx.Response(404)

        self.mock_http(handler)
        artifact = asyncio.run(TeamsGraphAdapter().fetch_artifact(self._hearing()))
        self.assertEqual(artifact.kind, "audio")
        self.assertEqual(artifact.data, b"mp4")

    def test_not_organizer_reports_actionable_error(self) -> None:
        self.mock_http(lambda r: httpx.Response(200, json={"value": []}))
        with self.assertRaisesRegex(AdapterError, "organised by this user"):
            asyncio.run(TeamsGraphAdapter().fetch_artifact(self._hearing()))


class HearingRoutesTests(AdapterTestCase):
    def setUp(self) -> None:
        super().setUp()
        app = FastAPI()
        app.include_router(hearings_router.router, prefix="/hearings")
        self.client = TestClient(app)

    def test_upload_persists_bytes_and_vtt_process_flow(self) -> None:
        matter = storage.create_matter(Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024"))
        created = self.client.post("/hearings/import/manual", json={"title": "Acme Holdings E123 of 2024 mention"}).json()
        hid = created["hearing"]["id"]

        # Processing before confirm is refused.
        self.assertEqual(self.client.post(f"/hearings/{hid}/process").status_code, 409)

        up = self.client.post(f"/hearings/{hid}/transcript", files={"file": ("t.vtt", VTT.encode(), "text/vtt")})
        self.assertEqual(up.status_code, 200, up.text)
        self.client.post(f"/hearings/{hid}/confirm", json={"decision": "confirm", "matter_id": str(matter.id)})

        resp = self.client.post(f"/hearings/{hid}/process", params={"wait": "true", "use_llm": "false"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["hearing"]["status"], "transcribed")
        self.assertEqual(body["asr"]["asr_provider"], "platform_transcript")
        self.assertEqual(body["proceedings"]["rules"][0]["date"], "2025-03-12")
        self.assertEqual(body["proceedings"]["rules"][0]["speaker"], "Hon. Justice Odhiambo")
        transcript = storage.get_transcript(__import__("uuid").UUID(body["session_id"]))
        self.assertEqual(transcript[0].start_ms, 1000)

        self.assertEqual(self.client.post(f"/hearings/{hid}/review").json()["status"], "reviewed")

    def test_audio_upload_actually_stored(self) -> None:
        created = self.client.post("/hearings/import/manual", json={"title": "x"}).json()
        hid = created["hearing"]["id"]
        resp = self.client.post(f"/hearings/{hid}/upload", files={"file": ("../evil.wav", b"RIFFdata", "audio/wav")})
        self.assertEqual(resp.status_code, 200, resp.text)
        key = resp.json()["recording_object_key"]
        self.assertTrue(key.endswith("/evil.wav"))
        from app.services import recording_store

        self.assertEqual(recording_store.load(key), b"RIFFdata")
