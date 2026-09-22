# HakiScribe

**The conversation is the work. The transcript is only the witness.**

> Sahara CodeSwitch Africa demo: [watch the HakiScribe walkthrough](https://youtu.be/FjsZqMBsCfs)

A legal work agent for the rooms where justice is spoken — client meetings, chambers, court. It listens from a phone, a laptop, or an [Omi](https://omi.me) wearable, then returns not a wall of text, but a tray of ready artifacts: a demand letter, a hearing date, a matter, a billable hour, a private note that will still be true on Monday.

Built for [AI Tinkerers Nairobi — Agents, Everywhere](https://nairobi.aitinkerers.org/). Built for lawyers, judges, and clerks. Built as the listening instrument of [HakiChain](https://hakichain.com).

[Repository](https://github.com/Isomkevin/haki-scribe) · [HakiChain](https://hakichain.com) · [Backend API docs](./hakiscribe-backend/README.md) · [Connector OAuth setup](./docs/CONNECTOR_OAUTH_SETUP.md) · [Judge submission](./SUBMISSION.md) · [Sahara CodeSwitch](./Sahara_CodeSwitch_Africa_Challenge_submission/README.md) · [Sahara demo video](https://youtu.be/FjsZqMBsCfs) · [Architecture / SPEC](./SPEC.md) · [Roadmap](./roadmap.md)

---

## Why an agent in the room — not another chatbot

Justice in Kenya — *haki* — is still, too often, handwritten. A judge converts notes into a proceeding after the fact. A lawyer reconstructs a client conversation from memory, and the detail that mattered is already gone. The delay is not a lack of intelligence. It is a lack of a record that can become work.

Most tools stop at the recording. They give you a transcript and call it done. A transcript is a means. It is not the deliverable. A legal professional is liable for what leaves their desk. They do not need another document to read. They need the next document to write — grounded, selectable, and traceable to the words that were actually spoken.

A standalone chatbot cannot do this. It is not in the room. It cannot be flagged without looking. It cannot refuse privileged speech before a model sees it. It cannot name Speaker 1 as John Kamau before a letter is drafted. HakiScribe can, because the environment *is* the workflow:

1. **Listen** — mic or Omi, English, Kiswahili, and the code-switch in which this work actually happens.
2. **Flag** — a thumb-sized control marks the contract term, the date, the admission, without breaking eye contact.
3. **Verify** — you name the speakers. You redact what must never leave the room. Nothing is silently deleted. Nothing is silently used.
4. **Propose** — the Action Tray, not a chat. Concrete, individually selectable pieces of legal work, each grounded in a line that was said.
5. **Decide** — you choose. You edit. Work that belongs in HakiChain and Ambiguous AI lands there. Liability stays with the human who was always going to carry it.

HakiScribe is that next document. Many of them. Chosen, not imposed.

---

## What it does

You record. You may never look at the screen.

A thumb-sized control — **Flag this moment** — lets you mark what mattered without breaking eye contact. Those flags become memory the product can honour later.

When the room goes quiet, HakiScribe asks two brief, serious questions first:

1. **Who was speaking?** Speaker 1 is not a name. A generated letter cannot say Speaker 1. You name the people, because this record may matter evidentially.
2. **What must never leave this room?** Privileged and off-record lines stay visible, struck through, and excluded from everything that follows.

Then it reads. What returns is the **Action Tray** — the heart of the product. Not a chat. Not a summary. A vertical list of concrete legal work:

- a draft letter, brief, or memo
- a follow-up on the calendar
- a matter opened or linked in the HakiChain workspace
- a contact brought up to date
- a billable time entry
- a private note

Every card tells you *why* it exists — explicitly stated, or inferred from context — and offers **View source**. Confidence is visible. Speculation is muted, and starts unchecked.

You choose. You generate. The draft arrives as a document you can still edit — never as a locked verdict. The calendar event is a real invitation (and a real `.ics`). The time entry looks like a timesheet line, because that is what it is.

Nothing is a dead end. Every session can be reopened. The library is a record of work done, not of recordings stored.

---

## Designed for the room, not the desk

The primary surface is a phone in a courtroom or across a table. Hands are often not free. The record button is unmistakable. The flag is large enough to find without looking. Live captions exist only to prove the tool is listening; they are never the headline.

Desktop is where review happens — the longer read, the careful edit, the decision about what leaves the building.

The product does not ask you to choose a document type before you speak. That would be the old world: templates first, reality second. HakiScribe listens first.

---

## Trust is the product

This is privileged speech. The interface is calm on purpose: deep ink, restrained gold, the typography of documents rather than of demos. No glowing orbs. No theatre.

A line stays visible while you record and while you choose:

**Not used to train models · GDPR compliant**

For this audience, that line is not decoration. It is why the tool is allowed in the room.

HakiScribe will propose. It will never pretend the proposal is the professional. You name the speakers. You redact what must not travel. You see the source. You select the work. You edit the draft before it leaves. The agent is in the room. The liability stays with the human who was always going to carry it.

---

## How it works

```
Phone / laptop mic                    Omi wearable
        │                                  │
        │  WebSocket audio chunks          │  transcript webhook
        ▼                                  ▼
                    FastAPI backend
           session · speakers · redaction · flags
                          │
           Trigger.dev (or in-process fallback)
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     Detect  (OpenRouter → GPT-4o)   Generate
     + Exa counterparty context      (OpenRouter → GPT-4o)
              │                       │
              └───────────┬───────────┘
                          ▼
                    Action Tray
                          │
     ┌──────────┬─────────┼─────────┬──────────┬──────────┐
     ▼          ▼         ▼         ▼          ▼          ▼
  Draft      Calendar   Matter    Contact   Time entry  Note
  letter     + .ics     (link or   update
     │          │       create)
     └──────────┴─────────┴─────────┘
                Ambiguous AI
           Docs · Calendar · CRM · Chat
                (or local-only)
```

Two LLM passes after transcription, not one:

1. **Detection** — reads the *non-redacted* transcript once, weighted by flagged moments and known matters, and proposes source-grounded artifacts.
2. **Generation** — for each artifact the professional selects, does the type-specific work. Drafts stay editable. Calendar events produce a real `.ics`. Matters link instead of duplicating when the client is already known.

---

## App surface

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Product landing — no sessions, transcripts, or client work |
| `/login` | Public | Workspace sign-in (email/password + temporary demo account) |
| `/new` | Private | Start a session, open the judge demo, past-session library |
| `/sessions/$sessionId` | Private | Record → speakers → privilege → Action Tray → generate |
| `/tracker` | Private | Case / matter tracker |
| `/research` | Private | Exa-backed legal research and news desk |
| `/settings` | Private | Profile, workspace defaults, security, connectors, about |
| `/connectors` | Private | Redirects to `/settings?section=connectors` |

Private routes use `RequireAuth`. Signed-out visits go to `/login?next=…` and return after sign-in. Accounts come from server `HAKISCRIBE_USERS` plus an optional demo account (`DEMO_LOGIN_ENABLED`). Everyone signed in currently shares one workspace; per-lawyer vaults are not built yet.

---

## Stack

| Layer | What we use |
|---|---|
| Frontend | React 19, TanStack Start, Vite, Tailwind CSS — mobile-first, built in Lovable |
| Backend | FastAPI, WebSockets; in-memory + local JSON by default, optional `DATABASE_URL` (Postgres), optional S3 draft archive |
| Capture | Browser MediaRecorder → `/sessions/{id}/stream`, or Omi Miniapp / legacy webhook |
| Speech | OpenRouter Whisper (`openai/whisper-large-v3`) by default; optional OpenAI / Groq Whisper; **Intron Sahara** for code-switch / legal refine (`ASR_PROVIDER=intron` or Settings → Connectors) |
| Agent | OpenRouter → OpenAI GPT-4o for detection and drafting |
| Durability | Trigger.dev at repo root (`src/trigger/`) — `detect-actions`, `generate-actions`, `research-actions` |
| Enrichment | Exa company search, citation crawl, and news monitors — context only, never drafted as fact |
| Connectors | Google Drive / Calendar, Dropbox, OneDrive (OAuth); Gemini (Vertex OAuth); Anthropic / OpenAI / Intron (verified keys) |
| Delivery | Ambiguous AI Docs, Calendar, CRM, and Chat review notifications; WhatsApp handoff for review |
| Auth | Server accounts + signed browser token (`POST /auth/login`) — not Supabase Auth |
| Deploy | Render Blueprint (`render.yaml`) — binds `0.0.0.0:$PORT` |

---

## Sponsor tools

Each integration is load-bearing, not a checkbox. Each degrades gracefully if its key is missing, so the pipeline still works and lights up as keys are added.

| Tool | What it does here |
|---|---|
| **OpenAI** | GPT-4o for detection and drafting (via OpenRouter). Whisper when `ASR_PROVIDER=openai`. |
| **OpenRouter** | Single routing layer for live captions, `/detect`, and `/generate`. |
| **Trigger.dev** | Durable, retried background execution of detect, generate, and research. Falls back in-process. |
| **Exa** | Counterparty lookup on Action Tray cards; research / citation crawl; news monitors. |
| **Ambiguous AI** | Real Docs, Calendar events, CRM deals/contacts, and a Chat ping when a draft is ready for a human — never auto-sent. |
| **Omi** | Wearable Miniapp (uid pairing) or legacy per-session webhook. |
| **Intron Sahara** | African code-switching ASR + legal court-hearing refine on multilingual Stop; Settings connector or `INTRON_API_KEY`. See [`submission/`](./submission/README.md). |
| **AI Tinkerers** | Built for the Nairobi *Agents, Everywhere* brief: agents that show up where people already work. |

---

## Team

**Kevin Isom** — Lead. Architecture, FastAPI pipeline (mic + Omi, speakers, redaction, flags), OpenRouter / OpenAI / Trigger.dev / Exa / Ambiguous integrations, Render deploy. Designed HakiScribe as HakiChain’s listening instrument.

**Mercy Wairimu** — Product and legal workflow. In-room experience: no-look Flag, speaker naming, privilege before the model, source-traced Action Tray, human review before anything leaves the desk. Mobile-first frontend and Kenyan practice (English / Kiswahili / code-switch, GDPR trust line).

---

## For judges (Agents, Everywhere)

The written description, demo path, and rubric mapping live in [`SUBMISSION.md`](./SUBMISSION.md).

1. Open [hakiscribe.lovable.app](https://hakiscribe.lovable.app/) (public landing).
2. **Sign in** → use **Use demo credentials** (temporary judging account), or email/password.
3. On `/new`, click **Open a completed judge demo** — Wanjiru Holdings client meeting (English/Kiswahili), privilege locked, Action Tray + generated letter.
4. Optional live path: start a mic or Omi session, flag a moment, name speakers, redact, detect, generate.

Omi: preferred path is the private Miniapp under **Settings → Connectors → Omi**. Legacy demos still work with `/webhooks/omi?session_id=<HakiScribe UUID>`. Share drafts over WhatsApp; chosen work can land in Ambiguous Docs, Calendar, and CRM, or in connected Drive / Dropbox / OneDrive / Google Calendar.

---

## Run it

**Backend**

```bash
cd hakiscribe-backend
pip install -r requirements.txt
cp .env.example .env.local   # at least OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cp .env.example .env.local   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

**Trigger.dev (optional — durable detect / generate / research)**

```bash
# Same .env.local as the frontend root; needs TRIGGER_SECRET_KEY + BACKEND_INTERNAL_*
npm run trigger:dev
```

Do **not** put secrets in the committed `.env` — Lovable publishes that file. Use `.env.local` locally and Render / Lovable Cloud Secrets in production. See [`.env.example`](./.env.example) and [`hakiscribe-backend/.env.example`](./hakiscribe-backend/.env.example).

Deploy the API with the repo-root [Render Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/Isomkevin/haki-scribe). The published Lovable app at [hakiscribe.lovable.app](https://hakiscribe.lovable.app/) reads `VITE_API_BASE_URL` from the repo-root `.env` (`https://hakiscribe-backend.onrender.com`). Republish after changing that value.

Connector OAuth (Google / Dropbox / Microsoft / Gemini) and workspace accounts: [`docs/CONNECTOR_OAUTH_SETUP.md`](./docs/CONNECTOR_OAUTH_SETUP.md). Demo the HTTP path without a microphone via [`hakiscribe-backend/README.md`](./hakiscribe-backend/README.md). Architecture and API contract: [`SPEC.md`](./SPEC.md).

### Docs map

| Doc | Use it for |
|---|---|
| [`README.md`](./README.md) (this file) | Product story, routes, stack, local run |
| [`hakiscribe-backend/README.md`](./hakiscribe-backend/README.md) | API runbook, auth, Omi Miniapp, demo HTTP path |
| [`src/routes/README.md`](./src/routes/README.md) | TanStack file-based routing conventions |
| [`SPEC.md`](./SPEC.md) | Architecture, data model, API contract |
| [`docs/CONNECTOR_OAUTH_SETUP.md`](./docs/CONNECTOR_OAUTH_SETUP.md) | Google / Dropbox / Microsoft / Gemini OAuth on Render |
| [`SUBMISSION.md`](./SUBMISSION.md) | AI Tinkerers Nairobi judge path |
| [`Sahara_CodeSwitch_Africa_Challenge_submission/`](./Sahara_CodeSwitch_Africa_Challenge_submission/README.md) | Sahara CodeSwitch Africa challenge packet |
| [`hakiscribe-backend/benchmarking/README.md`](./hakiscribe-backend/benchmarking/README.md) | ASR benchmark harness |
| [`roadmap.md`](./roadmap.md) | Done checklist + remaining external setup |

---

## A chapter of HakiChain

HakiScribe is not a sidecar chatbot. It is the listening instrument of [HakiChain](https://hakichain.com) — the parent product for legal work that already has a workspace, a matter, a calendar, a file. HakiLens, HakiDraft, and HakiReview already live on that desk. What we built for this hackathon is the agent in the room: live capture, Flag, speaker and privilege control, the Action Tray, and delivery into real tools.

What is spoken becomes what the practice already uses.

**Leave the room with the work already begun.**
