# HakiScribe ASR Benchmark — Sahara CodeSwitch Africa Challenge

Generated: run `python -m benchmarking.run_benchmark` from `hakiscribe-backend/` after recording clips.

## Models compared

| Provider | Role |
|----------|------|
| **sahara-intron** | Intron Sahara v2.5 — legal court-hearing mode (`file_category_legal`) |
| **openrouter-whisper** | Default HakiScribe live ASR (`openai/whisper-large-v3`) |
| **groq-whisper** / **openai-whisper** | Third baseline — Groq if `GROQ_API_KEY` set, else OpenAI |

## Metrics

- **WER / CER** — Levenshtein vs hand-written reference transcript
- **Entity accuracy** — share of `key_terms` from clip metadata found in hypothesis
- **Latency (ms)** — wall time per provider per clip

## Initial run (audio pending)

Clip templates and reference transcripts live in `hakiscribe-backend/benchmarking/test-clips/`. Until consented `.webm` files are recorded locally, the harness reports **skipped: audio missing** for each clip × provider.

| Clip | Provider | WER | CER | Entity acc. | Latency (ms) | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| clip_01 | sahara-intron | — | — | — | — | skipped: audio missing: clip_01.webm |
| clip_01 | openrouter-whisper | — | — | — | — | skipped: audio missing: clip_01.webm |
| clip_01 | groq-whisper | — | — | — | — | skipped: audio missing: clip_01.webm |
| … | … | … | … | … | … | (repeat for clip_02–clip_06) |

After recording, re-run the harness; copy fresh output from `benchmarking/out/BENCHMARK_RESULTS.md` over this file for submission.

## How to run

```bash
cd hakiscribe-backend
python -m benchmarking.run_benchmark
```

Requires: `INTRON_API_KEY` (or Intron connector), `OPENROUTER_API_KEY`, and `GROQ_API_KEY` or `OPENAI_API_KEY`.
