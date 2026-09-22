# Benchmark dataset provenance — HakiScribe

## Selected public source

**Dataset:** [Intron AfriSwitch](https://huggingface.co/datasets/intronhealth/AfriSwitch)  
**Configuration relevant to HakiScribe:** `swahili`, a Swahili–English code-switching test set  
**Split:** `test` only  
**Licence:** CC BY-NC-SA 4.0  
**Source status:** public benchmark; no data copied into this repository

## Why this source fits

HakiScribe targets English–Kiswahili legal conversations in Kenya. AfriSwitch supplies audio plus human transcripts for natural English–Swahili switching, including per-utterance code-mixing index, number of switch points, and duration. It is suitable for measuring transcription robustness; it is not a legal-domain benchmark, so it cannot by itself demonstrate legal entity accuracy.

## Pre-registered evaluation plan

Before any provider is called, select a fixed sample from the `swahili` test configuration using this rule:

1. Include only audio with an available human transcription.
2. Stratify the sample by code-mixing index (low, medium, high) and duration (short, medium, long).
3. Use a reproducible random seed and save selected Hugging Face sample IDs, dataset revision, and preprocessing commands.
4. Send exactly the same decoded audio bytes to Sahara, OpenRouter Whisper, and the third baseline.
5. Use AfriSwitch transcription as the reference for WER/CER; report mean, median, and per-stratum results.

Legal-entity accuracy will be reported only on the separate, consented, de-identified legal test clips in `hakiscribe-backend/benchmarking/test-clips/`, because AfriSwitch does not annotate legal entities.

## Data protection and redistribution

- Do not add AfriSwitch audio to Git, the deployed product, or a public submission attachment.
- Attribute Intron AfriSwitch and preserve the CC BY-NC-SA 4.0 conditions in any derivative analysis.
- Do not combine public audio with client material.
- Any locally recorded legal clip requires explicit consent, de-identification, and a human reference transcript.
