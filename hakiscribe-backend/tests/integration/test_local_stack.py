"""Opt-in integration tests against a REAL local inference stack.

Skipped unless HAKISCRIBE_IT_LOCAL=1. Needs:
  - Ollama at OLLAMA_BASE_URL with OLLAMA_MODEL pulled        (LLM tests)
  - faster-whisper server at LOCAL_WHISPER_BASE_URL            (ASR tests)
  - HAKISCRIBE_IT_AUDIO=<wav/m4a path>  and
    HAKISCRIBE_IT_AUDIO_EXPECT=<comma-separated words that must appear>

Every test runs in local_only mode and records the host of every outbound
httpx request; any non-loopback host fails the test (no cloud AI egress).

  HAKISCRIBE_IT_LOCAL=1 OLLAMA_BASE_URL=http://127.0.0.1:11434 OLLAMA_MODEL=gemma4 \
    python -m pytest tests/integration -v -s
"""

from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from pathlib import Path
from unittest import mock

import httpx

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, Matter, TranscriptSegment
from app.services import ai_mode, hearing_pipeline, hearings, inference_health, proceedings_intel, storage
from tests.stage_b_helpers import IsolatedStoreTestCase

ENABLED = os.environ.get("HAKISCRIBE_IT_LOCAL") == "1"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class EgressRecorder:
    """Patch httpx.AsyncClient.send to record every outbound host."""

    def __init__(self) -> None:
        self.hosts: list[str] = []
        self._orig = httpx.AsyncClient.send

    def __enter__(self):
        recorder = self

        async def send(client, request, *args, **kwargs):
            recorder.hosts.append(request.url.host)
            return await recorder._orig(client, request, *args, **kwargs)

        self._patch = mock.patch.object(httpx.AsyncClient, "send", send)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()

    def non_loopback(self) -> list[str]:
        return [h for h in self.hosts if h not in LOOPBACK]


def _seg(text: str, start: int, speaker: str) -> TranscriptSegment:
    return TranscriptSegment(session_id=uuid.uuid4(), text=text, start_ms=start, end_ms=start + 4000, speaker=speaker)


HEARING_TRANSCRIPT = [
    _seg("This is HCCC number E123 of 2024, Acme Holdings versus Baraka Traders.", 0, "Court"),
    _seg("I am Jane Wanjiru appearing for the plaintiff, Your Honour.", 5000, "Jane Wanjiru"),
    _seg("Mheshimiwa, mimi ni Peter Otieno kwa niaba ya mshtakiwa.", 10000, "Peter Otieno"),
    _seg("Your Honour, our witness is unwell and we seek an adjournment.", 15000, "Jane Wanjiru"),
    _seg("The defendant shall file and serve its witness statements within 14 days.", 20000, "Court"),
    _seg("The matter is adjourned to 12th March 2025 for hearing. Costs in the cause.", 25000, "Court"),
]


@unittest.skipUnless(ENABLED, "set HAKISCRIBE_IT_LOCAL=1 to run against the real local stack")
class LocalLlmTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_mode.clear_runtime_overrides()
        ai_mode.set_runtime_config(mode="local_only")
        health = asyncio.run(inference_health.check_ollama(deep=True))
        if not health.get("ok"):
            self.fail(f"Ollama not ready: {health.get('detail')}")

    def tearDown(self) -> None:
        ai_mode.clear_runtime_overrides()

    def test_proceedings_extraction_local_only(self) -> None:
        with EgressRecorder() as egress:
            result = asyncio.run(proceedings_intel.extract(HEARING_TRANSCRIPT))
        llm = result["llm"]
        print("\nLLM status:", llm["status"], "provider:", llm.get("provider"), "model:", llm.get("model"),
              "latency_ms:", llm.get("latency_ms"))
        for item in llm["items"]:
            print("  grounded:", item["kind"], {k: item.get(k) for k in ("date", "text", "name", "role")})
        for item in llm["ungrounded"]:
            print("  UNGROUNDED:", item["kind"], item.get("reason"), item.get("quote"))
        print("  egress hosts:", sorted(set(egress.hosts)))

        self.assertEqual(egress.non_loopback(), [])
        self.assertTrue(egress.hosts, "expected at least one call to local Ollama")
        self.assertEqual(llm["status"], "ok", llm.get("error"))
        self.assertEqual(llm["provider"], "Ollama (local)")
        dates = {i.get("date") for i in llm["items"] if i["kind"] == "next_date"}
        self.assertIn("2025-03-12", dates)
        self.assertIn("2025-03-12", {r["date"] for r in result["rules"]})


@unittest.skipUnless(ENABLED, "set HAKISCRIBE_IT_LOCAL=1 to run against the real local stack")
class LocalAsrPipelineTests(IsolatedStoreTestCase):
    def setUp(self) -> None:
        super().setUp()
        ai_mode.set_runtime_config(mode="local_only")
        health = asyncio.run(inference_health.check_local_whisper())
        if not health.get("ok"):
            self.skipTest(f"local whisper not reachable: {health.get('detail')}")
        self.audio = os.environ.get("HAKISCRIBE_IT_AUDIO")
        if not self.audio or not Path(self.audio).is_file():
            self.skipTest("HAKISCRIBE_IT_AUDIO not set")

    def test_recording_to_record_local_only(self) -> None:
        matter = storage.create_matter(Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024"))
        hearing = hearings.create_hearing(
            HearingCreate(source=HearingSource.manual_upload, title="Acme Holdings HCCC No. E123 of 2024 mention")
        )
        hearings.propose_matches(hearing.id)
        hearings.confirm_match(hearing.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id))
        data = Path(self.audio).read_bytes()
        hearing_pipeline.ingest_recording(hearing.id, Path(self.audio).name, data, "audio/wav")

        use_llm = os.environ.get("HAKISCRIBE_IT_SKIP_LLM") != "1"
        with EgressRecorder() as egress:
            result = asyncio.run(hearing_pipeline.process_hearing(hearing.id, use_llm=use_llm, language_hint="en"))

        segs = storage.get_transcript(uuid.UUID(result["session_id"]))
        text = " ".join(s.text for s in segs).lower()
        print("\nASR:", result["asr"])
        for s in segs:
            print(f"  [{s.start_ms/1000:6.2f}-{s.end_ms/1000:6.2f}] {s.text}")
        print("  rules:", [(r["date"], r["purpose"]) for r in result["proceedings"]["rules"]])
        if result["proceedings"]["llm"]:
            print("  llm:", result["proceedings"]["llm"]["status"],
                  [(i["kind"], i.get("date") or i.get("text")) for i in result["proceedings"]["llm"]["items"]])
        print("  egress hosts:", sorted(set(egress.hosts)))

        self.assertEqual(egress.non_loopback(), [])
        self.assertEqual(result["asr"]["asr_provider"], "local_whisper")
        self.assertGreater(len(segs), 1, "expected timestamped segments")
        self.assertTrue(all(s.end_ms >= s.start_ms for s in segs))
        for word in filter(None, (os.environ.get("HAKISCRIBE_IT_AUDIO_EXPECT") or "").split(",")):
            self.assertIn(word.strip().lower(), text)
        self.assertEqual(hearing.status.value, "transcribed")


if __name__ == "__main__":
    unittest.main()
