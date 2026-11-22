# 03 — Target architecture

## Goals

1. Run supported AI workflows on local / private inference when configured.
2. Keep frontier models (Claude, ChatGPT, Gemini, Nebius, OpenRouter, …) first-class in `cloud` and hybrid cloud routes.
3. Support explicit **hybrid** per-task routing.
4. Ingest virtual hearings (Calendar, Teams Graph, Zoom) and resolve matters with human confirmation when ambiguous.
5. File approved artifacts into HakiChain via existing ingress.

## Mode diagram

```
HAKISCRIBE_AI_MODE
  cloud       → existing ASR + LLM + research (default)
  hybrid      → HAKISCRIBE_ROUTE_{ASR,DETECT,DRAFT,ASK,RESEARCH}
  private     → NIM / Ollama / custom private URLs only
  local_only  → local_whisper + ollama only; research off; no cloud egress
```

## Inference topology (self-host)

```
deploy/local-inference/
  profile cpu  → faster-whisper HTTP + Ollama
  profile gpu  → NIM / vLLM-compatible + shared network
       ↓
  FastAPI (LocalWhisperProvider, OllamaChatProvider, nvidia_nim)
```

## Virtual court topology

```
google_calendar | teams_graph | zoom | manual_upload
       ↓
  Hearing record + Matter Resolution Engine
       ↓ (confirm if ambiguous)
  Session + recording ingest
       ↓
  Existing ASR → Detect → Generate → HakiChain file_*
```

## Non-goals (Stage A)

- Live meeting bots that join without official API support
- Replacing HakiChain document integrity on-chain
- Removing any frontier connector
