# HakiScribe resilience engineering pack

Shared source of truth for **local AI independence**, **hybrid cloud+local routing**, and **virtual court foundations**.

All agents (Cursor, Claude Code, reviewers) must:

1. Read this pack before changing inference, hearings, or court adapters.
2. Inspect code — docs can lag; verify in the repo.
3. Update [`08-implementation-status.md`](./08-implementation-status.md) and the relevant handoff before transferring work.
4. Never strip frontier connectors (Claude, ChatGPT, Gemini, Nebius, OpenRouter, etc.) or collapse `hybrid` into `local_only`.

## Documents

| Doc | Purpose |
| --- | --- |
| [01-current-architecture.md](./01-current-architecture.md) | Verified stack map |
| [02-ai-dependency-audit.md](./02-ai-dependency-audit.md) | Cloud AI call sites |
| [03-target-architecture.md](./03-target-architecture.md) | Target: modes, local, court, HakiChain |
| [04-virtual-court-assessment.md](./04-virtual-court-assessment.md) | Teams / Zoom / Calendar feasibility |
| [05-implementation-roadmap.md](./05-implementation-roadmap.md) | Phased milestones |
| [06-api-and-database-contracts.md](./06-api-and-database-contracts.md) | Interfaces, env, migrations |
| [07-agent-work-allocation.md](./07-agent-work-allocation.md) | Cursor vs Claude Code |
| [08-implementation-status.md](./08-implementation-status.md) | Living checklist |
| [09-testing-and-verification.md](./09-testing-and-verification.md) | Test plan |
| [10-decisions-and-risks.md](./10-decisions-and-risks.md) | ADRs |
| [11-is-hakiscribe-done.md](./11-is-hakiscribe-done.md) | Plain-English completion verdict (honest scorecard) |
| [12-hakichain-integration-contracts.md](./12-hakichain-integration-contracts.md) | Bidirectional HakiChain ingress contracts (`2026-11`) |
| [fixtures/hakichain-ingress-2026-11.json](./fixtures/hakichain-ingress-2026-11.json) | Shared ingress request/response fixtures |
| [handoffs/cursor-to-claude.md](./handoffs/cursor-to-claude.md) | Stage A → B handoff |
| [handoffs/claude-to-cursor.md](./handoffs/claude-to-cursor.md) | Stage B → C handoff (filled by Claude Code) |
| [handoffs/cursor-to-claude-hakichain-alignment.md](./handoffs/cursor-to-claude-hakichain-alignment.md) | Phase-1 HakiChain alignment handoff |

## Modes at a glance

| Mode | Meaning |
| --- | --- |
| `cloud` (default) | Current product behaviour; all frontier connectors |
| `hybrid` | Explicit per-task mix of cloud + local (+ private) |
| `private` | Self-hosted / VPC endpoints only |
| `local_only` | Compose local ASR/LLM only; fail closed |

Related product docs: [ARCHITECTURE.md](../../ARCHITECTURE.md), [nvidia-nim.md](../../nvidia-nim.md), [CONNECTOR_OAUTH_SETUP.md](../../CONNECTOR_OAUTH_SETUP.md).
