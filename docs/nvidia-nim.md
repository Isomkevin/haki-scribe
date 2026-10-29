# NVIDIA NIM on Brev

> **Hackathon note:** Nebius Token Factory + NVIDIA Nemotron is the default AI
> compute when `NEBIUS_API_KEY` is connected. Set `LLM_PROVIDER=nvidia_nim` only
> when you intentionally want self-hosted NIM instead. A connected Nebius key
> overrides a leftover `LLM_PROVIDER=openrouter` env value; it does **not**
> override an explicit `nvidia_nim` choice. When Nebius is selected, failures
> are surfaced — there is no silent OpenRouter switch.

HakiScribe can use self-hosted NVIDIA NIM services for live speech-to-text and
the detection/drafting passes. Deploy an ASR NIM with its OpenAI-compatible
transcription route and a Llama 3.1 8B Instruct NIM (or a larger model
appropriate for the allocated Brev GPU) with its OpenAI-compatible
chat-completions route.

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
`/v1/chat/completions`. If a selected NIM ASR service cannot be reached,
times out, or returns a non-2xx response, HakiScribe logs a warning and may
use the configured Whisper path for captions. For LLM, prefer Nebius when
connected; NIM LLM failures should be investigated rather than treated as a
silent success. `GET /health` includes a `nvidia_nim` object with configured
endpoint statuses. NIM is configured through backend environment variables; it
is not a Settings connector.

When `LLM_PROVIDER=nvidia_nim`, both detection and generation use the NIM LLM.
When Nebius is connected (and NIM is not forced), detection uses Nemotron Super
and drafting uses Ultra via Token Factory. Otherwise OpenRouter models from the
backend README apply.
