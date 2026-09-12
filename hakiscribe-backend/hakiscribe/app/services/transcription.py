"""
ASR provider abstraction. Every provider implements `transcribe_chunk`.
Routers only ever call `get_provider()` — never import a vendor SDK
directly outside this file. This is what makes the CodeSwitch Africa
Challenge swap (Whisper -> Intron Voice AI) a one-line change later.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class TranscriptionResult:
    def __init__(self, text: str, confidence: Optional[float] = None, raw: Optional[dict] = None):
        self.text = text
        self.confidence = confidence
        self.raw = raw or {}


def chunk_filename(audio_bytes: bytes) -> str:
    """Browsers (MediaRecorder) send WebM/Ogg Opus, not WAV. Whisper APIs
    pick the decoder from the filename extension, so sniff the container
    instead of always claiming .wav."""
    if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "chunk.webm"
    if audio_bytes[:4] == b"OggS":
        return "chunk.ogg"
    if audio_bytes[:4] == b"RIFF":
        return "chunk.wav"
    if audio_bytes[4:8] == b"ftyp":
        return "chunk.mp4"
    return "chunk.webm"


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        ...


class GroqWhisperProvider(TranscriptionProvider):
    """Fast Whisper inference via Groq. Good default for a live demo."""

    def __init__(self):
        from groq import AsyncGroq  # local import: keep this optional dependency isolated

        self.client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        # Groq's API wants a file-like object; wrap the raw bytes.
        import io

        file_ = (chunk_filename(audio_bytes), io.BytesIO(audio_bytes))
        resp = await self.client.audio.transcriptions.create(
            file=file_,
            model="whisper-large-v3",
            language=language_hint if language_hint in ("en", "sw") else None,
        )
        return TranscriptionResult(text=resp.text, raw=resp.model_dump() if hasattr(resp, "model_dump") else {})


class OpenAIWhisperProvider(TranscriptionProvider):
    """Default ASR provider — genuinely exercises the OpenAI sponsor
    integration, not just decoratively. Slower than Groq but often more
    accurate on code-switched Swahili/English in practice."""

    def __init__(self):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        import io

        file_ = (chunk_filename(audio_bytes), io.BytesIO(audio_bytes))
        resp = await self.client.audio.transcriptions.create(
            file=file_,
            model="whisper-1",
            language=language_hint if language_hint in ("en", "sw") else None,
        )
        return TranscriptionResult(text=resp.text)


class IntronVoiceProvider(TranscriptionProvider):
    """Stub for the Sahara CodeSwitch Africa Challenge submission.
    Fill in against Intron's actual API docs before that deadline."""

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        raise NotImplementedError("Wire this up against Intron Voice AI's API before the CodeSwitch submission.")


def get_provider() -> TranscriptionProvider:
    name = os.environ.get("ASR_PROVIDER", "openai").lower()
    if name == "groq":
        return GroqWhisperProvider()
    if name == "openai":
        return OpenAIWhisperProvider()
    if name == "intron":
        return IntronVoiceProvider()
    raise ValueError(f"Unknown ASR_PROVIDER: {name}")
