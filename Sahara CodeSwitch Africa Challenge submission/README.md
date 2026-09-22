# Sahara CodeSwitch Africa Challenge — HakiScribe submission

This folder packages deliverables for the **Legal & Public Services** track of the Intron Sahara CodeSwitch Africa Challenge.

## Contents

| File | Purpose |
|------|---------|
| [PROBLEM_AND_SOLUTION.md](./PROBLEM_AND_SOLUTION.md) | Problem framing and HakiScribe + Sahara approach |
| [BENCHMARK_RESULTS.md](./BENCHMARK_RESULTS.md) | Multi-model ASR comparison (Sahara vs Whisper baselines) |
| [RESPONSIBLE_AI.md](./RESPONSIBLE_AI.md) | Ethics, consent, privilege, data handling |
| [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) | One-take demo video script |
| [TECHNICAL_DOCUMENTATION.md](./TECHNICAL_DOCUMENTATION.md) | Architecture, Sahara integration, source locations, local run |
| [SUBMISSION_MANIFEST.md](./SUBMISSION_MANIFEST.md) | Final form mapping, links, and pre-submit checklist |
| [DATASET_PROVENANCE.md](./DATASET_PROVENANCE.md) | AfriSwitch source, licence, and fixed-sample evaluation plan |

## Code

- Main app: repository root [`README.md`](../README.md)
- Intron connector + Sahara refine: [`hakiscribe-backend/app/services/transcription.py`](../hakiscribe-backend/app/services/transcription.py), [`integrations.py`](../hakiscribe-backend/app/services/integrations.py)
- Benchmark harness: [`hakiscribe-backend/benchmarking/`](../hakiscribe-backend/benchmarking/)

## What's new for this challenge

1. **Intron Sahara connector** (API key) in Settings → Connectors
2. **Multilingual / code-switch sessions** refine with Sahara legal court-hearing mode on Stop
3. **Benchmark harness** comparing Sahara, OpenRouter Whisper, and Groq/OpenAI Whisper
4. **Test clip scaffolding** with challenge metadata under `benchmarking/test-clips/`

Default live ASR remains OpenRouter Whisper — Sahara is additive.
