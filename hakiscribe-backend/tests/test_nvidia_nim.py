import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services import generation, nvidia_nim, transcription


class _Response:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.is_success = status_code < 300

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("bad response", request=httpx.Request("POST", "https://nim"), response=httpx.Response(self.status_code))


class _Client:
    def __init__(self, response=None, error=None, **_kwargs):
        self.response = response
        self.error = error
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class NvidiaNimTests(unittest.IsolatedAsyncioTestCase):
    async def test_asr_adapter_posts_openai_compatible_transcription(self):
        client = _Client(_Response({"text": "Court is adjourned."}))
        with patch.dict(os.environ, {"NVIDIA_NIM_ASR_ENDPOINT": "https://nim.example/v1"}, clear=False), patch(
            "httpx.AsyncClient", return_value=client
        ):
            result = await transcription.NvidiaNimWhisperProvider().transcribe_chunk(b"RIFFaudio")

        self.assertEqual(result.text, "Court is adjourned.")
        self.assertEqual(client.calls[0][0], "https://nim.example/v1/audio/transcriptions")
        self.assertIn("file", client.calls[0][1]["files"])

    async def test_asr_falls_back_to_openrouter_when_nim_is_unreachable(self):
        fallback = transcription.TranscriptionResult("OpenRouter caption")
        client = _Client(error=httpx.ConnectError("offline"))
        with patch.dict(os.environ, {"NVIDIA_NIM_ASR_ENDPOINT": "https://nim.example"}, clear=False), patch(
            "httpx.AsyncClient", return_value=client
        ), patch("app.integrations.llm_client.api_key", return_value="or-key"), patch.object(
            transcription.OpenRouterWhisperProvider, "transcribe_chunk", new=AsyncMock(return_value=fallback)
        ) as openrouter:
            result = await transcription.NvidiaNimWhisperProvider().transcribe_chunk(b"RIFFaudio")

        self.assertEqual(result.text, "OpenRouter caption")
        openrouter.assert_awaited_once()

    async def test_llm_adapter_posts_openai_compatible_chat_completion(self):
        client = _Client(_Response({"choices": [{"message": {"content": "NIM answer"}}]}))
        with patch.dict(os.environ, {"NVIDIA_NIM_LLM_ENDPOINT": "https://nim.example/v1", "NVIDIA_NIM_LLM_MODEL": "meta/test"}, clear=False), patch(
            "httpx.AsyncClient", return_value=client
        ):
            result = await nvidia_nim.complete("system", "user")

        self.assertEqual(result, "NIM answer")
        self.assertEqual(client.calls[0][0], "https://nim.example/v1/chat/completions")
        self.assertEqual(client.calls[0][1]["json"]["model"], "meta/test")

    async def test_llm_falls_back_to_openrouter_when_nim_is_unreachable(self):
        fallback_client = _Client(_Response({"choices": [{"message": {"content": "OpenRouter answer"}}]}))
        with patch.dict(os.environ, {"LLM_PROVIDER": "nvidia_nim", "OPENROUTER_API_KEY": "or-key"}, clear=False), patch(
            "app.services.nvidia_nim.complete", new=AsyncMock(side_effect=httpx.ConnectError("offline"))
        ), patch("app.integrations.llm_client.api_key", return_value="or-key"), patch(
            "httpx.AsyncClient", return_value=fallback_client
        ):
            result = await generation.complete_text("system", "user")

        self.assertEqual(result, "OpenRouter answer")
        self.assertEqual(fallback_client.calls[0][0], generation.OPENROUTER_URL)
