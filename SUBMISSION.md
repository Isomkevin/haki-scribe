# HakiScribe — Agents, Everywhere (Nairobi)

**Title:** HakiScribe — the legal work agent in the room

**For:** Lawyers, judges, and clerks in Kenya. Built as the listening instrument of [HakiChain](https://hakichain.com).

**Live:** [hakiscribe.lovable.app](https://hakiscribe.lovable.app/) · API [hakiscribe-backend.onrender.com](https://hakiscribe-backend.onrender.com/health)

**Repo:** [github.com/Isomkevin/haki-scribe](https://github.com/Isomkevin/haki-scribe)

---

## What we built

Most legal AI still waits in a chat window. HakiScribe shows up where the work already happens:

- **In the room** — a phone microphone or an [Omi](https://omi.me) wearable. A thumb-sized **Flag this moment** control marks the contract term, the date, or the admission without breaking eye contact.
- **In the pocket** — generated drafts and dates share to **WhatsApp** for human review. Kenyan practice already lives there. Nothing is auto-sent as advice.
- **At the desk** — the Action Tray proposes a demand letter, hearing, matter, CRM update, time entry, and private note. Chosen work lands in Ambiguous Docs / Calendar / CRM, or stays local if those keys are absent.

The transcript is a witness. The deliverable is the next document — source-traced, selectable, and editable.

## Why the environment matters

A standalone chatbot cannot do this. It is not in the room. It cannot be flagged without looking. It cannot refuse privileged speech before a model sees it. It cannot name Speaker 1 as James Wanjiru before a letter is drafted.

HakiScribe’s constraints are the product:

1. Listen (mic WebSocket or official Omi webhook shapes).
2. Flag moments that bias detection.
3. Name speakers. Redact privilege — redacted lines stay visible and never reach the model.
4. Detect a tray of artifacts, each grounded in a source line.
5. The professional chooses, edits, then generates.

Liability stays with the human who was always going to carry it.

## How to demo (2 minutes)

1. Open [hakiscribe.lovable.app](https://hakiscribe.lovable.app/).
2. Click **Open a completed judge demo** — a Kilimani construction meeting (English + Kiswahili), speakers named, tax advice locked, Action Tray + demand letter + calendar already generated.
3. Open **View source** on a card. Download the draft. Tap **WhatsApp review**.
4. Optional live path: **Start recording**, speak for 20 seconds, flag a date, name speakers, redact one line, generate.

Omi pairing URL is copied from an Omi session screen:  
`/webhooks/omi?session_id=<HakiScribe UUID>`

## Stack (sponsor tools, each load-bearing)

| Tool | Role |
|---|---|
| OpenRouter / OpenAI | Whisper captions + GPT-4o detect/draft |
| Trigger.dev | Durable detect/generate, in-process fallback |
| Exa | Counterparty background on tray cards — never drafted as fact |
| Ambiguous AI | Docs, Calendar, CRM, Chat ping for human review |
| Omi | Wearable transcript webhook |

Every integration degrades locally if its key is missing. The pipeline still completes.

## How this maps to the rubric

**Core functionality.** End-to-end: capture → flag → speakers → privilege → detect → select → generate. Judge demo works without a microphone.

**Innovation & theme.** The room, WhatsApp, and the legal desk are not wrappers. Flag, redact, and the Action Tray cannot be reproduced as “paste a transcript into chat.”

**Technical execution.** FastAPI + two LLM passes, ASR abstraction, official Omi payloads, Trigger.dev fallback, per-action error isolation, Kenyan document engine.

**Usefulness & agentic experience.** Source quotes, confidence, human selection, editable drafts, WhatsApp handoff, workspace links. The agent proposes. The professional decides.
