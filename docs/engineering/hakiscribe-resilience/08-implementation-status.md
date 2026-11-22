# 08 — Implementation status

Updated at end of Cursor Stage A.

| Item | Status | Notes |
| --- | --- | --- |
| Engineering doc pack | done | `docs/engineering/hakiscribe-resilience/` |
| `ai_mode` + hybrid routes | done | `ai_mode.py`, `/integrations/ai-mode` |
| Local Whisper + Ollama | done | Additive providers; Compose CPU stack |
| Compose CPU/GPU | done | `deploy/local-inference/` |
| Hearings schema/API | done | migration 003 + in-memory demo store |
| Court adapters | done | Calendar import; Teams/Zoom list + OAuth stubs |
| Settings / hearing UI | done | Settings → AI mode; Tracker hearings panel |
| Unit tests | done | `test_ai_mode`, `test_matter_resolution` + regression 23 passed |
| cursor-to-claude handoff | done | `handoffs/cursor-to-claude.md` |

## Frontier / hybrid invariants

- [x] Default mode is `cloud`
- [x] Claude / ChatGPT / Gemini connectors still listed in cloud + hybrid cloud routes
- [x] `local_only` blocks cloud without affecting cloud default
- [x] Hybrid route matrix persisted and visible (env + Settings UI)
