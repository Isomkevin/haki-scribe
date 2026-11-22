"""Backend ↔ local Whisper server contract, without the faster-whisper runtime.

Loads the real deploy/local-inference/faster-whisper/server.py with a stub
WhisperModel and routes LocalWhisperProvider's HTTP into it over ASGI. This
proves request/response shapes and the hearing pipeline wiring; it does NOT
measure transcription accuracy (see tests/integration for real-model runs).
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
import uuid
from pathlib import Path
from unittest import mock

import httpx
from fastapi.testclient import TestClient

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, Matter
from app.services import ai_mode, hearing_pipeline, hearings, storage
from tests.stage_b_helpers import IsolatedStoreTestCase

SERVER_DIR = Path(__file__).resolve().parents[2] / "deploy" / "local-inference" / "faster-whisper"


class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text
        self.avg_logprob, self.no_speech_prob = -0.2, 0.01


class _Info:
    language, language_probability, duration = "en", 0.98, 30.0


class StubWhisperModel:
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, path, **kwargs):
        StubWhisperModel.calls.append(kwargs)
        segs = [
            _Seg(0.0, 4.2, " Your Honour, we seek an adjournment."),
            _Seg(4.5, 9.0, " The matter is adjourned to 12th March 2025 for hearing."),
            _Seg(9.5, 10.0, "   "),
        ]
        return iter(segs), _Info()


def load_server():
    stub = types.ModuleType("faster_whisper")
    stub.WhisperModel = StubWhisperModel
    saved = {name: sys.modules.get(name) for name in ("faster_whisper", "server", "diarize")}
    sys.modules["faster_whisper"] = stub
    sys.path.insert(0, str(SERVER_DIR))
    try:
        sys.modules.pop("server", None)
        sys.modules.pop("diarize", None)
        server = importlib.import_module("server")
    finally:
        sys.path.remove(str(SERVER_DIR))
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod
    return server


class ServerContractTests(IsolatedStoreTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server()

    def setUp(self) -> None:
        super().setUp()
        StubWhisperModel.calls.clear()
        self.client = TestClient(self.server.app)

    def test_json_default_is_backward_compatible(self) -> None:
        body = self.client.post("/v1/audio/transcriptions", files={"file": ("c.webm", b"x")}).json()
        self.assertEqual(set(body), {"text", "model"})
        self.assertIn("adjourned to 12th March 2025", body["text"])

    def test_verbose_json_segments_and_legal_prompt(self) -> None:
        body = self.client.post(
            "/v1/audio/transcriptions",
            files={"file": ("h.wav", b"x")},
            data={"response_format": "verbose_json", "prompt": "Kenyan English and Kiswahili", "language": "sw"},
        ).json()
        self.assertEqual(len(body["segments"]), 2)  # blank segment dropped
        self.assertEqual(body["segments"][1]["start"], 4.5)
        self.assertEqual(body["language"], "en")
        self.assertEqual(body["diarization"], {"enabled": False, "reason": "not requested"})
        kwargs = StubWhisperModel.calls[-1]
        self.assertTrue(kwargs["vad_filter"])
        self.assertEqual(kwargs["language"], "sw")
        self.assertIn("Mheshimiwa", kwargs["initial_prompt"])
        self.assertIn("Kenyan English and Kiswahili", kwargs["initial_prompt"])

    def test_diarization_requested_but_disabled_says_why(self) -> None:
        body = self.client.post(
            "/v1/audio/transcriptions",
            files={"file": ("h.wav", b"x")},
            data={"response_format": "verbose_json", "diarize_speakers": "true"},
        ).json()
        self.assertFalse(body["diarization"]["enabled"])
        self.assertIn("DIARIZATION_ENABLED", body["diarization"]["reason"])
        self.assertTrue(all(s.get("speaker") is None for s in body["segments"]))

    def test_rejects_empty_and_unknown_format(self) -> None:
        self.assertEqual(self.client.post("/v1/audio/transcriptions", files={"file": ("e.wav", b"")}).status_code, 400)
        r = self.client.post("/v1/audio/transcriptions", files={"file": ("e.wav", b"x")}, data={"response_format": "srt"})
        self.assertEqual(r.status_code, 400)

    def test_assign_speakers_by_overlap(self) -> None:
        from importlib import util

        spec = util.spec_from_file_location("diarize_under_test", SERVER_DIR / "diarize.py")
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        segs = [{"start": 0, "end": 4}, {"start": 4.5, "end": 9}, {"start": 20, "end": 21}]
        turns = [{"start": 0, "end": 4.4, "speaker": "SPK_07"}, {"start": 4.4, "end": 10, "speaker": "SPK_02"}]
        out = mod.assign_speakers(segs, turns)
        self.assertEqual([s["speaker"] for s in out], ["Speaker 1", "Speaker 2", None])

    def test_hearing_pipeline_through_server_local_only(self) -> None:
        """Recording → LocalWhisperProvider → server.py (stub model) → session transcript."""
        ai_mode.set_runtime_config(mode="local_only")
        app = self.server.app
        real_client = httpx.AsyncClient

        def asgi_client(*args, **kwargs):
            kwargs["transport"] = httpx.ASGITransport(app=app)
            return real_client(*args, **kwargs)

        matter = storage.create_matter(Matter(client_name="Acme", matter_name="E1 of 2024"))
        hearing = hearings.create_hearing(HearingCreate(source=HearingSource.manual_upload, title="Acme E1 of 2024"))
        hearings.confirm_match(hearing.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        hearing_pipeline.ingest_recording(hearing.id, "h.wav", b"RIFF-audio", "audio/wav")

        # LocalWhisperProvider imports httpx inside the method, so patch the module attribute.
        with mock.patch.object(httpx, "AsyncClient", asgi_client):
            result = asyncio.run(hearing_pipeline.process_hearing(hearing.id, use_llm=False))

        self.assertEqual(result["asr"]["asr_provider"], "local_whisper")
        self.assertEqual(result["asr"]["segmentation"], "timestamped")
        segs = storage.get_transcript(uuid.UUID(result["session_id"]))
        self.assertEqual([(s.start_ms, s.end_ms) for s in segs], [(0, 4200), (4500, 9000)])
        self.assertEqual(result["proceedings"]["rules"][0]["date"], "2025-03-12")
        self.assertEqual(result["proceedings"]["rules"][0]["start_ms"], 4500)
        self.assertEqual(hearing.status.value, "transcribed")
