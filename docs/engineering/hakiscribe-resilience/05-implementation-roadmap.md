# 05 — Implementation roadmap

## Stage A (Cursor) — foundations

1. Engineering doc pack
2. `ai_mode` + hybrid route matrix + health
3. Local Whisper + Ollama adapters (additive)
4. Compose CPU/GPU profiles
5. Hearings schema + matter resolution API + manual upload + Calendar import
6. Teams + Zoom adapter interfaces / OAuth stubs
7. Settings UI for mode + hybrid routes + hearing confirm
8. Tests + `cursor-to-claude` handoff

## Stage B (Claude Code) — specialized

1. faster-whisper / WhisperX runtime hardening, EN/SW optimization
2. Diarization pipeline
3. Deep Teams/Zoom recording download flows where APIs allow
4. Authorized capture bots only if officially supported
5. Proceedings intelligence extraction with quote grounding
6. Integration tests against real sandbox accounts

## Stage C (Cursor) — verification

1. Review Claude Code diffs against this pack
2. Frontend/backend consistency
3. Migrations, regression, Local-Only traffic proof
4. Final report

## Dependency order

```
docs → ai_mode → local providers → compose
                ↘ health / settings UI
hearings schema → matter resolution → calendar import
                → teams/zoom adapters → UI confirm
tests → handoff
```
