# Problem and solution — HakiScribe for access to justice in Kenya

## The problem

Kenya's courts and legal aid desks run on spoken work — hearings, client intakes, rulings, and instructions — but the official record still depends on slow manual transcription. Backlogs grow when every proceeding must be typed before orders, letters, and matter files can move. Global speech models trained on Western monolingual speech break down on **Kenyan English–Kiswahili code-switching** and on legal names, amounts, and case references that matter in real filings.

This is a **population-scale** access-to-justice problem: not one firm's convenience, but millions of citizens waiting on courts and legal aid that cannot keep pace with how people actually speak in Kenyan legal rooms.

## Our solution

**HakiScribe** is HakiChain's listening instrument for legal practice. It captures live conversation (microphone or Omi wearable), transcribes multilingually, and — critically — does not stop at a transcript. After recording, an **Action Tray** proposes concrete legal artifacts grounded in what was said: draft letters, calendar events, matters, CRM entries, and billable time. The lawyer selects, edits, and generates — traceable to source segments.

For the Sahara CodeSwitch challenge we add **Intron Sahara v2.5** as a first-class connector:

- **Live captions** stay on OpenRouter Whisper for responsiveness (unchanged hackathon default).
- For **English + Kiswahili** or **Multilingual / African code-switch** sessions, **Stop** triggers a Sahara sync pass with `file_category_legal` and court-hearing formatting — replacing live captions with a refined legal transcript before speaker labeling, privilege control, and Action Tray detection.
- Settings → Connectors → **Intron Sahara (Voice AI)** stores the API key (workspace `INTRON_API_KEY` fallback).

The downstream agentic loop — privilege redaction, speaker relabel, detect, generate — is unchanged. Voice completes real legal work; Sahara improves the witness transcript for African multilingual speech.

## Why Intron fits

Intron already deploys judiciary transcription in African courts (e.g. Nigeria). HakiScribe extends that pattern to Kenyan advocates and clerks with an agent layer that turns speech into deliverables inside HakiChain's existing desk (HakiDraft, HakiLens, HakiReview).

## Benchmark

We compare Sahara against OpenRouter Whisper and Groq/OpenAI Whisper on consented code-switched legal clips (`hakiscribe-backend/benchmarking/`). Results: [BENCHMARK_RESULTS.md](./BENCHMARK_RESULTS.md).
