# 10 — Decisions and risks (ADRs)

## ADR-001: Frontier models remain first-class

**Decision:** Default `HAKISCRIBE_AI_MODE=cloud`. Local providers are additive. Never remove Anthropic, OpenAI, Gemini, Groq, Mistral, OpenRouter, Nebius, `claude_custom`, or NIM paths.

**Why:** Product quality and existing deployments depend on frontier models when connected.

## ADR-002: Hybrid is explicit per-task routing

**Decision:** Mode `hybrid` uses `HAKISCRIBE_ROUTE_*` (and Settings UI). No silent cloud↔local swap. Optional fallback only when `HAKISCRIBE_HYBRID_FALLBACK=explicit_allow` and logged in `ai_runs`.

**Why:** Firms need local ASR for privacy with Claude/ChatGPT for drafting without air-gapping the whole desk.

## ADR-003: Four modes, not a boolean

**Decision:** `cloud` | `hybrid` | `private` | `local_only`.

- `private` = self-hosted/VPC endpoints (NIM, Ollama, custom URL), no public SaaS AI
- `local_only` = Compose local only, fail closed

## ADR-004: Virtual court starts with ingest + matter resolution

**Decision:** Stage A ships Calendar import, manual upload, Teams/Zoom OAuth+list contracts, and confidence-based matter matching with human confirm. Live bots deferred to Stage B where official APIs allow.

## ADR-005: Compose under `deploy/local-inference/`

**Decision:** Keep root clean for Lovable dual-deploy; no platform-specific `vercel.json` unless required.

## Risks

| Risk | Mitigation |
| --- | --- |
| Over-broad cloud block breaks frontier in cloud/hybrid | Mode- and route-scoped gates + regression tests |
| NIM ASR silent Whisper fallback in local_only | Disable cross-realm fallback when mode forbids cloud |
| Trigger.dev cloud worker in local_only | Prefer in-process when `local_only` |
| Zoom/Teams admin policy blocks recordings | Document; never fabricate join |
| Hybrid misconfig | Validate routes against connected creds + health before save |
