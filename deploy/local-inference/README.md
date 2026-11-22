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

## Without Docker (verified on Windows 11, CPU-only, 2026-11-23)

```powershell
# Whisper server (short venv path avoids Windows long-path failures)
python -m venv $env:LOCALAPPDATA\HakiScribe\wv
& $env:LOCALAPPDATA\HakiScribe\wv\Scripts\python.exe -m pip install --only-binary=:all: -r deploy\local-inference\faster-whisper\requirements.txt
cd deploy\local-inference\faster-whisper
$env:WHISPER_MODEL="small"; $env:WHISPER_COMPUTE_TYPE="int8"
& $env:LOCALAPPDATA\HakiScribe\wv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001

# Ollama (installed app) — pick a model that fits RAM; 3B is practical on 16 GB CPU-only
ollama pull qwen2.5:3b
```

Backend: `HAKISCRIBE_AI_MODE=local_only`, `OLLAMA_MODEL=qwen2.5:3b`, `LOCAL_WHISPER_BASE_URL=http://127.0.0.1:8001`.

Measured on an i5-8250U / 16 GB / no GPU: Whisper `small` transcribes ~33 s of English audio in ~15–45 s;
qwen2.5:3b proceedings extraction takes 2–3 min per short hearing (`OLLAMA_TIMEOUT_S` defaults to 600).

## faster-whisper server API

`POST /v1/audio/transcriptions` (OpenAI-compatible multipart):

| Field | Default | Notes |
| --- | --- | --- |
| `response_format` | `json` | `json` → `{text, model}` (live captions). `verbose_json` → adds `segments[{start,end,text,avg_logprob,no_speech_prob,speaker?}]`, `language`, `duration`, `diarization`. |
| `language` | auto | `en`, `sw`, … |
| `prompt` | — | Appended to the built-in EN/SW court vocabulary prompt (`WHISPER_LEGAL_PROMPT`). |
| `diarize_speakers` | `false` | Needs the diarization build + `DIARIZATION_ENABLED=1` + `HF_TOKEN`; otherwise the response says why speakers are absent. |

`GET /health` reports `model_loaded` and diarization status; `POST /ready` force-loads the model.
VAD is always on (`WHISPER_VAD_MIN_SILENCE_MS`, `WHISPER_VAD_SPEECH_PAD_MS`).

Language safeguards (from real Kiswahili measurements, see 09):

- The built-in court-vocabulary prompt is applied only when the caller explicitly sets a language in
  `WHISPER_LEGAL_PROMPT_LANGS` (default `en`). On Kiswahili it raised WER and was sometimes emitted verbatim.
- Any segment repeating ≥5 consecutive prompt words is dropped (`prompt_echo_dropped` in the response).
- Auto-detection is limited to `WHISPER_ALLOWED_LANGUAGES` (default `en,sw`); `language_forced_from`
  reports an override (e.g. a Kiswahili clip detected as Javanese). Pick Kiswahili explicitly when known —
  it is measurably better than auto.

Hearing recordings use `verbose_json` through `LocalWhisperProvider.transcribe_file`; Teams/Zoom
WebVTT transcripts bypass ASR and keep the platform's participant names.

## Verify against the real stack

```bash
# Ollama must actually generate, not just list models:
curl "http://127.0.0.1:8000/integrations/ai-mode?deep=true"

cd hakiscribe-backend
HAKISCRIBE_IT_LOCAL=1 OLLAMA_BASE_URL=http://127.0.0.1:11434 OLLAMA_MODEL=<pulled model> \
LOCAL_WHISPER_BASE_URL=http://127.0.0.1:8001 \
HAKISCRIBE_IT_AUDIO=/path/hearing.wav HAKISCRIBE_IT_AUDIO_EXPECT=adjourned,March \
  python -m pytest tests/integration -v -s
```

Both integration tests run in `local_only` and fail if any request leaves loopback.

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
| Model listed but every call 500s ("llama-server binary not found") | Ollama install is incomplete (e.g. interrupted auto-update) — reinstall Ollama; `?deep=true` health catches this |
| pip install fails on Windows with a missing deep path | Enable Windows long paths or install into a short directory |
| `transcription failed: open() got an unexpected keyword argument 'metadata_errors'` | PyAV ≥ 15 with faster-whisper 1.2.x — `requirements.txt` pins `av<15`; reinstall |
| Proceedings LLM `error: ReadTimeout` | CPU generation slower than `OLLAMA_TIMEOUT_S`; raise it or use a smaller model |
| Ollama upgrade failed with "not enough space" and generation 500s | Free disk; the CPU runner is only ~45 MB of `lib/ollama` (GPU libs are the bulk) |
| Cloud still called | Ensure mode is `local_only` and routes are not overridden to public providers |
