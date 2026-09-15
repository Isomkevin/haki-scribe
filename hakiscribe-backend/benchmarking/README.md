# HakiScribe ASR benchmark (Sahara CodeSwitch Africa Challenge)

Compares **Intron Sahara**, **OpenRouter Whisper**, and **Groq/OpenAI Whisper** on consented code-switched legal audio clips.

## Run

```bash
cd hakiscribe-backend
python -m benchmarking.run_benchmark
```

Outputs:

- `benchmarking/out/benchmark_report.json`
- `benchmarking/out/BENCHMARK_RESULTS.md`

## Clips

Record or drop audio under `test-clips/` (≤90s, WebM/WAV). Each clip needs:

- `clip_XX.meta.json` — challenge metadata
- `clip_XX.reference.txt` — human reference transcript
- `clip_XX.webm` (or set `audio_file` in meta)

See `test-clips/README.md` for recording guidance.

## Env

- `INTRON_API_KEY` or Intron connector — Sahara runs
- `OPENROUTER_API_KEY` — Whisper baseline (default app ASR)
- `GROQ_API_KEY` or `OPENAI_API_KEY` — third model

Missing keys produce explicit `skipped` rows instead of failing the harness.
