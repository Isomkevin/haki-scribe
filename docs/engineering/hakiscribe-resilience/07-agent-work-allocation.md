# 07 — Agent work allocation

## Cursor Stage A (this session)

- Docs pack
- `ai_mode.py`, `inference_health.py`
- Local Whisper + Ollama adapters
- Compose under `deploy/local-inference/`
- Hearings migration + API + matter resolution
- Calendar / Teams / Zoom adapter foundations
- Settings + hearing confirm UI
- Unit tests + `handoffs/cursor-to-claude.md`

## Claude Code Stage B

- Production-harden local STT (WhisperX, VAD, EN/SW)
- Diarization + alignment
- Full Zoom/Teams recording pipelines
- Meeting bots only via official APIs
- Proceedings intelligence with citation grounding
- Load/perf and sandbox E2E

## Cursor Stage C

- Integration review, regression, docs consolidation, final report

## Rules

- One agent modifies shared code at a time
- Do not overwrite another agent’s implementation
- Do not remove frontier providers
- Do not claim untested integrations work
