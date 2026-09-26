# NVIDIA NIM on Brev

HakiScribe can use self-hosted NVIDIA NIM services for live speech-to-text and
the detection/drafting passes while retaining OpenRouter as a per-request
fallback. Deploy an ASR NIM with its OpenAI-compatible transcription route and
a Llama 3.1 8B Instruct NIM (or a larger model appropriate for the allocated
Brev GPU) with its OpenAI-compatible chat-completions route.

Expose each container through Brev's HTTPS proxy or another TLS-terminating
reverse proxy. The backend accepts either the service base URL (for example,
`https://asr.example`) or a URL ending in `/v1`; it adds the compatible routes
itself.

```env
ASR_PROVIDER=nvidia_nim
LLM_PROVIDER=nvidia_nim
NVIDIA_NIM_ASR_ENDPOINT=https://asr.example/v1
NVIDIA_NIM_LLM_ENDPOINT=https://llm.example/v1
NVIDIA_NIM_LLM_MODEL=meta/llama-3.1-8b-instruct
# Only when your proxy or NIM container requires Bearer authentication:
NVIDIA_NIM_API_KEY=
```

The ASR route is `/v1/audio/transcriptions` and the LLM route is
`/v1/chat/completions`. If either selected NIM service cannot be reached,
times out, or returns a non-2xx response, HakiScribe logs a warning and uses
the existing OpenRouter Whisper or GPT-4o request path instead. `GET /health`
includes a `nvidia_nim` object with the configured endpoint statuses.
