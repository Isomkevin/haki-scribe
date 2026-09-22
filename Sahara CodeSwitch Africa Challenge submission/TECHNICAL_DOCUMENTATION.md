# HakiScribe technical documentation — Sahara CodeSwitch Africa

## Product and architecture

HakiScribe is a mobile-first legal-work agent for lawyers, judges, and clerks. It captures a browser-microphone or Omi conversation, produces a transcript, lets the professional identify speakers and redact privileged segments, then proposes selectable legal-work artifacts in an Action Tray. Every output is reviewed and editable by a human.

```text
Microphone / Omi transcript
        ↓
FastAPI session service → live ASR captions
        ↓ (on Stop for configured code-switch sessions)
Intron Sahara legal refinement
        ↓
speaker naming + privilege redaction
        ↓
action detection → human selection → type-specific generation
        ↓
editable draft / calendar / matter / CRM / time entry / note
```

## Sahara integration

- Configure Sahara through **Settings → Connectors → Intron Sahara (Voice AI)** or server-side `INTRON_API_KEY`.
- Live captions use OpenRouter Whisper for responsive feedback.
- On Stop, English–Kiswahili, supported African code-switch, or multilingual sessions can undergo Sahara legal/court-hearing refinement before speaker naming, redaction, and action detection.
- If the connector/key is unavailable, the app keeps the existing transcript and does not claim Sahara processing.

## Source locations

| Concern | Location |
| --- | --- |
| Frontend | `src/` |
| Backend API and session pipeline | `hakiscribe-backend/app/` |
| Transcription and Sahara refinement | `hakiscribe-backend/app/services/transcription.py` |
| Connector handling | `hakiscribe-backend/app/services/integrations.py` |
| Benchmark harness | `hakiscribe-backend/benchmarking/` |
| Architecture and API contract | `SPEC.md` |
| OAuth / connector setup | `docs/CONNECTOR_OAUTH_SETUP.md` |

## Run locally

```bash
cd hakiscribe-backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# from repository root
npm install
npm run dev
```

Put secrets in `.env.local` or deployment secret storage, never version control. `OPENROUTER_API_KEY` supports the default ASR/agent flow, `INTRON_API_KEY` enables Sahara, and a third-provider key is needed for benchmark comparison. See `.env.example` and `hakiscribe-backend/.env.example`.

## Trust and safety

Users can redact transcript segments before language-model detection or generation. Generated work remains source-grounded, selectable, and editable; it is never automatically sent as legal advice. See `submission/RESPONSIBLE_AI.md` for known limitations and data handling.
