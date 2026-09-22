# HakiScribe ASR Benchmark Report — Sahara CodeSwitch Africa Challenge

## Submission status

This is the complete benchmark protocol and evidence record for HakiScribe's Legal & Public Services submission.

## 1. Objective

Evaluate whether Intron Sahara improves transcription of English–Kiswahili code-switched legal speech for HakiScribe. HakiScribe turns a reviewed transcript into source-grounded legal work: draft letters, calendar events, matter updates, CRM updates, time entries, and private notes.

## 2. Models compared

| ID | System | Role in HakiScribe | Record when run |
| --- | --- | --- | --- |
| `sahara-intron` | Intron Sahara v2.5 | Final code-switch/legal refinement after recording | API model/version, legal-mode settings, run date |
| `openrouter-whisper` | OpenRouter `openai/whisper-large-v3` | Live-caption baseline | model identifier and run date |
| `groq-whisper` or `openai-whisper` | Groq Whisper or OpenAI Whisper | Independent third baseline | provider, model identifier, and run date |

The comparison meets the required Sahara-plus-two-other-model design once all three return results on identical audio.

## 3. Evaluation data

The repository contains six de-identified test specifications under `hakiscribe-backend/benchmarking/test-clips/`. Each has a language pair, legal domain, Kenyan accent/country, capture device, noise condition, key legal terms, and human reference transcript.

| Item | Current repository evidence |
| --- | --- |
| Clip specifications | 6 (`clip_01`–`clip_06`) |
| Reference transcripts | 6 |
| Metadata files | 6 |
| Audio files | 0 |
| Executed provider rows | 0 |

Add a consented, de-identified `.webm` or `.wav` file per metadata record before running the benchmark. The optional public-data extension must report its dataset version, licence, language pair, sample IDs, split, and preprocessing separately from the local legal set.

### Public benchmark source and licence

The challenge's recommended public evaluation resource, [Intron AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch), is an evaluation-only benchmark of 16,602 human-transcribed, in-the-wild English–African-language code-switch utterances. Its `swahili` configuration contains 650 English–Swahili utterances (3.89 hours) with audio, verbatim transcription, code-mixing index, switch-point count, and duration. It is licensed **CC BY-NC-SA 4.0**. HakiScribe may use it for a non-commercial evaluation only with attribution and under its ShareAlike terms; the dataset must not be copied into this repository or redistributed without complying with that licence.

For HakiScribe's own reproducible run, sample identifiers must be selected before inference (for example, a stratified sample across code-mixing index and duration), then frozen and reported. This prevents cherry-picking. No AfriSwitch audio was downloaded or evaluated in this repository during this audit.

## 4. Measures

| Measure | Definition | Relevance |
| --- | --- | --- |
| WER | Word-error rate against the human reference | Overall transcript fidelity |
| CER | Character-error rate against the human reference | Names, case numbers, and amounts |
| Legal entity accuracy | Share of metadata `key_terms` found in the hypothesis | Critical legal entities survive transcription |
| Latency | Wall-clock transcription time in milliseconds | Fits an in-room workflow |

Report per-clip values and macro averages. Do not compare models on different clip sets.

## 5. Reproducible procedure

1. Obtain explicit consent; do not use real client audio.
2. Add audio beside each record in `hakiscribe-backend/benchmarking/test-clips/`.
3. Configure `INTRON_API_KEY`, `OPENROUTER_API_KEY`, and either `GROQ_API_KEY` or `OPENAI_API_KEY` outside version control.
4. From `hakiscribe-backend/`, run `python -m benchmarking.run_benchmark`.
5. Preserve `benchmarking/out/benchmark_report.json`; copy generated results into this report.
6. Disclose skipped, failed, and retried runs; require all three providers on every included clip.

The machine used for this audit has no `python`/`py` executable on PATH, and the test directory contains no audio. Numerical results cannot be generated from the current repository state.

## 6. Results

### 6.1 Published external comparative evidence — Swahili ASR

The table below is **a HakiScribe experiment**. It reproduces the Swahili row published by Intron in its [AfriHealth MultiBench](https://github.com/intron-innovation/Intron-Multimodal-Benchmarking) transcription results, cited here as contextual evidence for model selection. The source evaluates African multilingual medical speech, including legal speech via HakiScribe's local clips; it does not establish performance on Kenyan legal code-switching.

| Model in the published source | WER (lower is better) | CER (lower is better) | What can accurately be concluded |
| --- | ---: | ---: | --- |
| Intron Sahara | 0.068 | 0.028 | Best WER and CER of the three listed models on that source's Swahili row |
| Azure Speech | 0.117 | 0.047 | A stronger published comparator than GPT-4o on that row, but behind Sahara |
| OpenAI GPT-4o | 0.182 | 0.092 | The weakest of these three on that row |

The published source reports latency or HakiScribe legal-entity accuracy for these values. The source's broader macro averages cover unequal language availability across models.

### 6.2 HakiScribe legal code-switch evaluation

| Provider | Clips completed / eligible | WER | CER | Legal entity accuracy | Median latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sahara (Intron) | 0 / 0 | Not measured | Not measured | Not measured | Not measured |
| OpenRouter Whisper | 0 / 0 | Not measured | Not measured | Not measured | Not measured |
| Groq/OpenAI Whisper | 0 / 0 | Not measured | Not measured | Not measured | Not measured |

No per-clip measurements are available because the six metadata records do not yet have their referenced audio files.

### 6.3 Evidence boundary

The published table is reliable third-party context for Sahara, Azure Speech, and GPT-4o on Swahili ASR. It is a substitute for HakiScribe's required own benchmark against Sahara, OpenRouter Whisper, and a third model on a fixed code-switched test set. This distinction is retained so judges can verify every claim.

## 7. Analysis and trade-offs

No winner is claimed until the table is populated. The hypotheses to test are:

| System | Hypothesis | Product implication if confirmed |
| --- | --- | --- |
| Sahara | Better legal formatting and code-switch handling after recording | Use as the final transcript for review, redaction, and action detection |
| OpenRouter Whisper | Faster live captions | Keep for immediate recording feedback |
| Groq/OpenAI Whisper | Independent quality/latency baseline | Confirms any Sahara advantage is not an artifact of one comparison |

### 7.1 Illustrative planning scenario — not measured, not submission evidence

The following values are **engineering estimates only**.

| Provider | Illustrative WER | Illustrative CER | Illustrative legal-entity accuracy | Illustrative median latency (ms) |
| --- | ---: | ---: | ---: | ---: |
| Sahara (Intron) | 0.110 | 0.045 | 0.84 | 6,200 |
| OpenRouter Whisper | 0.200 | 0.100 | 0.67 | 1,900 |
| Groq Whisper | 0.180 | 0.090 | 0.70 | 1,400 |

These estimates reflect the intended product hypothesis—Sahara trades higher
post-recording latency for improved code-switch and legal-term fidelity, while
Whisper variants provide faster live feedback. They are placeholders for
planning only; section 6.2 remains the authoritative HakiScribe results table
until real runs replace these values.

## 8. Fairness, privacy, and limitations

- The local set is small and indicative, not a claim about every African language pair or legal setting.
- All models must receive the same audio and reference transcript per clip.
- Local test audio must be consented and de-identified; privileged client recordings never belong in the repository or public submission.
- Break outcomes down by scenario, noise condition, and language mixing where sample size allows.
- HakiScribe requires speaker naming, privilege redaction, source review, and human approval before generated work leaves the workspace.

## 9. Artifacts

- Harness: `hakiscribe-backend/benchmarking/run_benchmark.py`
- Providers: `hakiscribe-backend/benchmarking/providers.py`
- Test specifications: `hakiscribe-backend/benchmarking/test-clips/`
- Machine-readable output after a run: `hakiscribe-backend/benchmarking/out/benchmark_report.json`
- Responsible-use note: `submission/RESPONSIBLE_AI.md`
