# Local inference (CPU / GPU)

Optional stack for `HAKISCRIBE_AI_MODE=local_only`, `private`, or hybrid routes to `local_whisper` / `ollama`.

**Cloud mode does not require this stack.** Frontier connectors keep working without Compose.

## Quick start (CPU)

```bash
cd deploy/local-inference
cp .env.example .env
docker compose --profile cpu up -d --build
docker compose exec ollama ollama pull llama3.1
```

Point the FastAPI backend (see `hakiscribe-backend/.env.example`):

```env
HAKISCRIBE_AI_MODE=local_only
LOCAL_WHISPER_BASE_URL=http://127.0.0.1:8001
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1
```

Hybrid example (local captions + frontier drafting):

```env
HAKISCRIBE_AI_MODE=hybrid
HAKISCRIBE_ROUTE_ASR=local_whisper
HAKISCRIBE_ROUTE_DETECT=nebius
HAKISCRIBE_ROUTE_DRAFT=anthropic
HAKISCRIBE_ROUTE_ASK=openai
HAKISCRIBE_ROUTE_RESEARCH=tavily_exa
```

## GPU profile

Requires NVIDIA Container Toolkit. Starts `vllm` in addition to whisper/ollama:

```bash
docker compose --profile gpu up -d --build
```

You may instead keep using existing `NVIDIA_NIM_*` endpoints documented in `docs/nvidia-nim.md`.

## Offline / air-gap

1. Pre-pull images and models on a connected machine.
2. Transfer volumes / image tarballs.
3. Set `HAKISCRIBE_AI_MODE=local_only` and confirm `GET /health` shows local probes ok and no cloud routes.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Empty captions | `curl http://127.0.0.1:8001/health` |
| Detect fails in local_only | `curl http://127.0.0.1:11434/api/tags` and `ollama pull` |
| Cloud still called | Ensure mode is `local_only` and routes are not overridden to public providers |
