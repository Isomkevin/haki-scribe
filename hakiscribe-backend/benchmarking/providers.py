"""
Benchmark ASR adapters.

Third model choice: Groq Whisper when GROQ_API_KEY is set, else OpenAI Whisper.
Both are hosted Whisper baselines — swap to a non-Whisper API later if needed.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class AsrOutcome:
    transcript: str
    latency_ms: int
    raw: dict
    skipped: bool = False
    skip_reason: Optional[str] = None


class AsrProvider(Protocol):
    name: str

    async def transcribe(self, audio_bytes: bytes, filename: str, language_hint: Optional[str]) -> AsrOutcome:
        ...


class SaharaProvider:
    name = "sahara-intron"

    async def transcribe(self, audio_bytes: bytes, filename: str, language_hint: Optional[str]) -> AsrOutcome:
        from app.services.transcription import IntronVoiceProvider, intron_configured

        if not intron_configured():
            return AsrOutcome(
                transcript="",
                latency_ms=0,
                raw={},
                skipped=True,
                skip_reason="awaiting_api_key — connect Intron in Settings or set INTRON_API_KEY",
            )
        started = time.perf_counter()
        result = await IntronVoiceProvider().transcribe_file(
            audio_bytes,
            filename=filename,
            language_hint=language_hint,
            legal=True,
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        return AsrOutcome(
            transcript=result.text or "",
            latency_ms=elapsed,
            raw=result.raw if isinstance(result.raw, dict) else {"raw": result.raw},
        )


class OpenRouterWhisperBenchmark:
    name = "openrouter-whisper"

    async def transcribe(self, audio_bytes: bytes, filename: str, language_hint: Optional[str]) -> AsrOutcome:
        from app.integrations import llm_client
        from app.services.transcription import OpenRouterWhisperProvider

        if not llm_client.api_key():
            return AsrOutcome(
                transcript="",
                latency_ms=0,
                raw={},
                skipped=True,
                skip_reason="OPENROUTER_API_KEY not configured",
            )
        started = time.perf_counter()
        result = await OpenRouterWhisperProvider().transcribe_chunk(audio_bytes, language_hint=language_hint)
        elapsed = int((time.perf_counter() - started) * 1000)
        return AsrOutcome(
            transcript=result.text or "",
            latency_ms=elapsed,
            raw=result.raw if isinstance(result.raw, dict) else {},
        )


class GroqWhisperBenchmark:
    name = "groq-whisper"

    async def transcribe(self, audio_bytes: bytes, filename: str, language_hint: Optional[str]) -> AsrOutcome:
        from app.services.transcription import GroqWhisperProvider

        if not os.environ.get("GROQ_API_KEY"):
            return AsrOutcome(
                transcript="",
                latency_ms=0,
                raw={},
                skipped=True,
                skip_reason="GROQ_API_KEY not configured",
            )
        started = time.perf_counter()
        result = await GroqWhisperProvider().transcribe_chunk(audio_bytes, language_hint=language_hint)
        elapsed = int((time.perf_counter() - started) * 1000)
        return AsrOutcome(
            transcript=result.text or "",
            latency_ms=elapsed,
            raw=result.raw if isinstance(result.raw, dict) else {},
        )


class OpenAIWhisperBenchmark:
    name = "openai-whisper"

    async def transcribe(self, audio_bytes: bytes, filename: str, language_hint: Optional[str]) -> AsrOutcome:
        from app.services.transcription import OpenAIWhisperProvider

        if not os.environ.get("OPENAI_API_KEY"):
            return AsrOutcome(
                transcript="",
                latency_ms=0,
                raw={},
                skipped=True,
                skip_reason="OPENAI_API_KEY not configured",
            )
        started = time.perf_counter()
        result = await OpenAIWhisperProvider().transcribe_chunk(audio_bytes, language_hint=language_hint)
        elapsed = int((time.perf_counter() - started) * 1000)
        return AsrOutcome(
            transcript=result.text or "",
            latency_ms=elapsed,
            raw=result.raw if isinstance(result.raw, dict) else {},
        )


def benchmark_providers() -> list[AsrProvider]:
    third: AsrProvider = GroqWhisperBenchmark() if os.environ.get("GROQ_API_KEY") else OpenAIWhisperBenchmark()
    return [SaharaProvider(), OpenRouterWhisperBenchmark(), third]
