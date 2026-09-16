"""
ASR provider abstraction. Every provider implements `transcribe_chunk`.
Routers only ever call `get_provider()` — never import a vendor SDK
directly outside this file. This is what makes the CodeSwitch Africa
Challenge swap (Whisper -> Intron Voice AI) a one-line change later.

Intron Sahara is also used for full-file refine on multilingual /
code-switch sessions via `transcribe_file` (legal court-hearing mode).
"""

import asyncio
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


def audio_format(audio_bytes: bytes) -> str:
    """OpenRouter STT wants wav/mp3/flac/m4a/ogg/webm/aac, not mp4."""
    ext = chunk_filename(audio_bytes).rsplit(".", 1)[-1]
    return "m4a" if ext == "mp4" else ext


CODE_SWITCH_PROMPT = (
    "This conversation mixes Kenyan English and Kiswahili, including code-switching. "
    "Transcribe both languages faithfully. Do not translate."
)

SAHARA_SYNC_URL = "https://infer.voice.intron.io/file/v1/upload/sync"
SAHARA_STATUS_URL = "https://infer.voice.intron.io/file/v1/status"


def whisper_language(language_hint: Optional[str]) -> Optional[str]:
    from app.services.languages import whisper_iso_language

    return whisper_iso_language(language_hint)


def whisper_prompt(language_hint: Optional[str]) -> Optional[str]:
    from app.services.languages import whisper_code_switch_prompt

    return whisper_code_switch_prompt(language_hint)


def sahara_language(language_hint: Optional[str]) -> str:
    """Map HakiScribe session hints to Sahara use_language_asr_input codes."""
    from app.services.languages import sahara_asr_code

    return sahara_asr_code(language_hint)


def intron_api_key() -> Optional[str]:
    from app.services import integrations

    creds = integrations.get_creds("intron") or {}
    key = (creds.get("api_key") or os.environ.get("INTRON_API_KEY") or "").strip()
    return key or None


def intron_configured() -> bool:
    return bool(intron_api_key())


def should_refine_with_sahara(
    language_hint: Optional[str],
    *,
    detected_mode: Optional[str] = None,
    transcript_text: Optional[str] = None,
) -> bool:
    """Sahara refine for African / pair sessions or detected code-switching."""
    if not intron_configured():
        return False
    from app.services.language_detect import needs_sahara_refine

    return needs_sahara_refine(
        language_hint,
        detected_mode=detected_mode,
        transcript_text=transcript_text,
    )


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        ...


class OpenRouterWhisperProvider(TranscriptionProvider):
    """Live captions through the same OpenRouter key used for detection
    and drafting. Default model is openai/whisper-large-v3 — a Whisper
    slug on OpenRouter, not a second OpenAI account."""

    def __init__(self):
        from app.integrations import llm_client

        key = llm_client.api_key()
        if not key:
            raise KeyError("OPENROUTER_API_KEY")
        self.api_key = key
        self.model = os.environ.get("ASR_MODEL", "openai/whisper-large-v3")

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        import base64

        import httpx

        payload: dict = {
            "model": self.model,
            "input_audio": {
                "data": base64.b64encode(audio_bytes).decode("ascii"),
                "format": audio_format(audio_bytes),
            },
        }
        language = whisper_language(language_hint)
        if language:
            payload["language"] = language
        prompt = whisper_prompt(language_hint)
        if prompt:
            payload["prompt"] = prompt

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except Exception:  # noqa: BLE001 — keep the live session open
            return TranscriptionResult(text="", raw={"error": "openrouter_transcription_failed"})

        return TranscriptionResult(text=body.get("text") or "", raw=body if isinstance(body, dict) else {})


class GroqWhisperProvider(TranscriptionProvider):
    """Fast Whisper inference via Groq. Good default for a live demo."""

    def __init__(self):
        from groq import AsyncGroq  # local import: keep this optional dependency isolated

        self.client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        # Groq's API wants a file-like object; wrap the raw bytes.
        import io

        file_ = (chunk_filename(audio_bytes), io.BytesIO(audio_bytes))
        kwargs: dict = {"file": file_, "model": "whisper-large-v3", "language": whisper_language(language_hint)}
        prompt = whisper_prompt(language_hint)
        if prompt:
            kwargs["prompt"] = prompt
        resp = await self.client.audio.transcriptions.create(**kwargs)
        return TranscriptionResult(text=resp.text, raw=resp.model_dump() if hasattr(resp, "model_dump") else {})


class OpenAIWhisperProvider(TranscriptionProvider):
    """Optional direct OpenAI Whisper when ASR_PROVIDER=openai."""

    def __init__(self):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        import io

        file_ = (chunk_filename(audio_bytes), io.BytesIO(audio_bytes))
        kwargs: dict = {"file": file_, "model": "whisper-1", "language": whisper_language(language_hint)}
        prompt = whisper_prompt(language_hint)
        if prompt:
            kwargs["prompt"] = prompt
        resp = await self.client.audio.transcriptions.create(**kwargs)
        return TranscriptionResult(text=resp.text)


class IntronVoiceProvider(TranscriptionProvider):
    """Intron Sahara v2.5 — African code-switching ASR.

    Live chunks use sync upload without legal post-processing (latency).
    Full-file refine (`transcribe_file`) enables legal court-hearing mode
    for the product multilingual / CodeSwitch demo path.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or intron_api_key() or "").strip()

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        if not self.api_key:
            return TranscriptionResult(text="", raw={"error": "intron_not_configured"})
        return await self.transcribe_file(
            audio_bytes,
            filename=chunk_filename(audio_bytes),
            language_hint=language_hint,
            legal=False,
        )

    async def transcribe_file(
        self,
        audio_bytes: bytes,
        *,
        filename: Optional[str] = None,
        language_hint: Optional[str] = None,
        legal: bool = True,
    ) -> TranscriptionResult:
        if not self.api_key:
            return TranscriptionResult(text="", raw={"error": "intron_not_configured"})

        import httpx

        name = filename or chunk_filename(audio_bytes)
        mime = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "mp4": "audio/mp4",
            "m4a": "audio/mp4",
            "ogg": "audio/ogg",
            "webm": "audio/webm",
            "flac": "audio/flac",
        }.get(name.rsplit(".", 1)[-1].lower(), "application/octet-stream")

        data: dict[str, str] = {
            "audio_file_name": name,
            "use_language_asr_input": sahara_language(language_hint),
        }
        if legal:
            data["use_category"] = "file_category_legal"
            data["get_legal_court_hearing"] = "TRUE"

        try:
            async with httpx.AsyncClient(timeout=130) as client:
                response = await client.post(
                    SAHARA_SYNC_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"audio_file_blob": (name, audio_bytes, mime)},
                    data=data,
                )
                body = _safe_json(response)
                if response.status_code == 503:
                    file_id = _extract_file_id(body)
                    if not file_id:
                        return TranscriptionResult(
                            text="",
                            raw={"error": "intron_503_without_file_id", "body": body},
                        )
                    return await self._poll_status(client, file_id)
                if response.status_code >= 400:
                    return TranscriptionResult(
                        text="",
                        raw={"error": "intron_http_error", "status": response.status_code, "body": body},
                    )
                return _result_from_sahara_payload(body)
        except Exception as exc:  # noqa: BLE001 — keep product sessions open
            return TranscriptionResult(text="", raw={"error": "intron_transcription_failed", "detail": str(exc)})

    async def _poll_status(self, client, file_id: str, *, max_attempts: int = 40, delay_s: float = 3.0) -> TranscriptionResult:
        for _ in range(max_attempts):
            response = await client.get(
                f"{SAHARA_STATUS_URL}/{file_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"get_structured_post_processing": "t"},
            )
            body = _safe_json(response)
            data = body.get("data") if isinstance(body, dict) else None
            status = (data or {}).get("processing_status") if isinstance(data, dict) else None
            if status == "FILE_TRANSCRIBED":
                return _result_from_sahara_payload(body)
            if status == "FILE_PROCESSING_FAILED":
                return TranscriptionResult(text="", raw={"error": "intron_processing_failed", "body": body})
            await asyncio.sleep(delay_s)
        return TranscriptionResult(text="", raw={"error": "intron_poll_timeout", "file_id": file_id})


def _safe_json(response) -> dict:
    try:
        body = response.json()
        return body if isinstance(body, dict) else {"raw": body}
    except Exception:  # noqa: BLE001
        return {"raw_text": (response.text or "")[:500]}


def _extract_file_id(body: dict) -> Optional[str]:
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict) and data.get("file_id"):
        return str(data["file_id"])
    if body.get("file_id"):
        return str(body["file_id"])
    return None


def _result_from_sahara_payload(body: dict) -> TranscriptionResult:
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        data = body if isinstance(body, dict) else {}
    text = (
        data.get("audio_transcript")
        or data.get("legal_court_hearing")
        or data.get("transcript")
        or data.get("text")
        or ""
    )
    if isinstance(text, dict):
        text = text.get("text") or text.get("transcript") or str(text)
    raw = dict(body) if isinstance(body, dict) else {"body": body}
    raw["provider"] = "sahara"
    return TranscriptionResult(text=str(text).strip(), raw=raw)


class UnavailableProvider(TranscriptionProvider):
    """Keeps a live mic session open when no ASR key is configured.
    Chunks produce no captions; Flag / Stop / later segment injection still work."""

    async def transcribe_chunk(self, audio_bytes: bytes, language_hint: Optional[str] = None) -> TranscriptionResult:
        return TranscriptionResult(text="", raw={"error": "ASR is not configured"})


def get_provider() -> TranscriptionProvider:
    from app.integrations import llm_client

    name = os.environ.get("ASR_PROVIDER", "openrouter").lower()
    if name == "openrouter":
        return OpenRouterWhisperProvider() if llm_client.api_key() else UnavailableProvider()
    if name == "groq":
        return GroqWhisperProvider() if os.environ.get("GROQ_API_KEY") else UnavailableProvider()
    if name == "openai":
        return OpenAIWhisperProvider() if os.environ.get("OPENAI_API_KEY") else UnavailableProvider()
    if name == "intron":
        return IntronVoiceProvider() if intron_configured() else UnavailableProvider()
    raise ValueError(f"Unknown ASR_PROVIDER: {name}")
