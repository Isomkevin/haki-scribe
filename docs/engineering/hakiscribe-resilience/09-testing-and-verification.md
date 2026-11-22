# 09 — Testing and verification

## Stage A automated

- `ai_mode` resolve defaults to `cloud`
- `local_only` rejects cloud ASR/LLM/research provider ids
- `hybrid` resolves per-task routes independently
- Matter resolution: high confidence vs ambiguous (requires confirm)
- Existing privilege / tray tests still pass

## Local AI (manual / Stage B+)

- Disconnect cloud keys; enable `local_only`; run transcription + detect with Compose
- EN + Kiswahili samples
- Simulate local down → explicit error, queue/retry behaviour
- Prove no outbound AI host traffic in `local_only`

## Virtual court

- Calendar import → match → confirm → session
- Ambiguous match blocked until confirm
- Teams/Zoom: OAuth configured → list metadata (sandbox)
- Manual upload path end-to-end

## Regression

- `cloud` mode detect/generate/Ask with Nebius or OpenRouter
- Connector cards still connect Anthropic/OpenAI/Gemini
- Trigger.dev path when keyed (cloud/hybrid only)
