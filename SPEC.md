# HakiScribe — Build Spec

**What it is:** An audio-capture legal work companion. It records legal
conversations and court proceedings (via phone/laptop mic or the Omi
wearable), transcribes them multilingually (English/Swahili and
code-switched speech), and — this is the actual product, not a bonus
feature — analyzes the finished transcript to surface a tray of concrete
legal artifacts the professional can generate from it: a draft document
(letter/brief/memo), a follow-up calendar event, a new or existing matter
in HakiChain Workspace, a CRM update, a billable time entry, a private
note. The user picks which ones to generate, like reviewing a pull
request, not like reading a transcript. Raw transcription is a means,
not the deliverable.

**Why:** Judges convert handwritten notes into court proceedings by hand
(a real source of delay). Lawyers recall client conversations from memory
after the fact, and lose details. HakiScribe removes the transcription
step and hands legal professionals a searchable, structured record.

**For legal professionals specifically**, trust and control matter as
much as the AI itself: everything the tray proposes has to be traceable
back to what was actually said, privileged/off-record moments must never
reach the model, and speaker attribution needs to be a real name, not
"Speaker 1" — because this record might matter evidentially. Sections 3
and 5 below build those constraints in rather than bolting them on.

**Targets:** AI Tinkerers Nairobi "Agents, Everywhere" hackathon (today) —
built to the actual brief: agents that show up where people already
work, not another standalone chat window. HakiScribe's home base is
literally in the room (the Omi wearable), and its output lands in real
tools (Ambiguous AI's Docs, Calendar, CRM) rather than a bespoke
dashboard. Also targets a planned entry into the Sahara CodeSwitch
Africa Challenge (Intron Voice AI), Legal & Public Services track — so
the transcription layer should be swappable, not hard-wired to one ASR
vendor.

---

## 1. Scope for today

Two audio paths into one pipeline:

1. **Mic capture** (phone/laptop, browser-based) — live audio streamed to
   the backend in chunks, transcribed near-real-time. Includes a
   no-look **Flag this moment** control the user can tap mid-conversation
   without breaking eye contact — it drops a timestamped bookmark that
   later biases detection toward what the user already knew mattered.
2. **Omi wearable** — Omi does on-device/cloud capture and pushes
   transcript segments to a webhook you register. You are not receiving
   raw audio from Omi in the common case — you're receiving its
   transcript payload. Treat it as a second transcript *source*, not a
   second ASR provider.

Both paths converge on the same `Session` / `TranscriptSegment` data
model, so downstream processing doesn't care which path produced the
transcript.

## 2. Architecture

```
┌─────────────┐        ┌──────────────────┐
│  Mic client │──WS───▶│                  │
│ (browser)   │        │                  │      ┌───────────────┐
└─────────────┘        │   FastAPI        │─────▶│ Supabase (meta │
                        │   backend        │      │ + auth)        │
┌─────────────┐        │                  │      └───────────────┘
│ Omi webhook │──HTTP─▶│  - session mgr   │
│ (their cloud)│       │  - ASR provider  │      ┌───────────────┐
└─────────────┘        │    abstraction   │─────▶│ Cloudflare R2  │
                        │  - speaker relabel│     │ (audio blobs,  │
                        │  - redaction      │     │  EU region)    │
                        │  - matter registry│     └───────────────┘
                        └────────┬─────────┘
                                 │
                     trigger-and-wait (Trigger.dev, falls back to
                     in-process if not configured — see §8)
                                 │
                        ┌────────┴─────────┐
                        │  action detector │  (OpenRouter → OpenAI)
                        │  action executor │
                        └────────┬─────────┘
                                 │
        ┌────────────┬──────────┼──────────┬────────────┬────────────┐
        ▼             ▼         ▼          ▼            ▼            ▼
   Draft doc      Calendar   Workspace    CRM        Time entry   Private
  (LLM, real,    event (real, matter      update     (real,       note
  → Ambiguous     → Ambiguous (real, new  (Ambiguous  storage)    (real)
   Docs +          Calendar +  or linked,  best-effort,
   Chat notify)    .ics)       → Ambiguous stub if not
                               CRM deal)   configured)
```

The pipeline has two LLM passes after transcription, not one:
1. **Detection** (`action_detector.py`) — reads the *non-redacted*
   transcript once, weighted by any flagged moments and aware of known
   existing matters, and proposes a list of candidate artifacts with
   extracted fields and a source-grounding quote.
2. **Generation** (`action_executor.py`) — for each artifact the user
   selects, does the type-specific work. draft_document, private_note,
   calendar_event, and time_entry are all real; workspace_matter creates
   or links a real `Matter` and mirrors it into Ambiguous AI's CRM when
   configured; crm_entry attempts a best-effort Ambiguous CRM contact call.

Both passes run through `trigger_client.trigger_and_wait()`, which
prefers executing as a Trigger.dev background task (durable, retried,
observable) and transparently falls back to calling the exact same
Python logic in-process when Trigger.dev isn't configured — see §8.

No document type is chosen up front. The UI's job is showing the tray
and letting the user pick, not routing them through a template picker.

- **Backend:** FastAPI (matches HakiChain's existing microservice stack),
  so it slots into the same AWS deployment later.
- **ASR provider abstraction:** one interface, multiple backends —
  Whisper (via Groq or OpenAI, fast + good multilingual baseline) today,
  Intron Voice AI as a swap-in for the CodeSwitch challenge. Never call
  a specific vendor SDK outside of `app/services/transcription.py`.
- **Storage:** session/transcript/matter metadata in Supabase (already
  in use for HakiChain auth); raw audio blobs in Cloudflare R2 (EU
  region, already the ODPC-aligned choice for HakiChain).
- **Frontend:** built separately in Lovable, mobile-first. A prompt for
  that build comes once this backend contract is settled.

## 3. Data model

```
Session
  id: uuid
  title: str
  source: "mic" | "omi"
  language_hint: str | null      # e.g. "en", "sw", "code-switch"
  status: "recording" | "processing" | "ready" | "exported"
  created_at, updated_at

TranscriptSegment
  id: uuid
  session_id: uuid (fk)
  speaker: str | null            # diarization label, or a real name after relabel
  text: str
  start_ms: int
  end_ms: int
  confidence: float | null
  source_raw: json               # original payload from ASR/Omi, for audit
  redacted: bool                 # true = excluded from detection (privilege/off-record)

FlaggedMoment                     # the no-look "Flag this moment" bookmark
  id: uuid
  session_id: uuid (fk)
  at_ms: int
  label: str | null

Matter                            # persistent client/matter registry, for continuity
  id: uuid
  client_name: str
  matter_name: str
  created_at

DetectedAction
  id: uuid
  session_id: uuid (fk)
  type: "draft_document" | "calendar_event" | "workspace_matter"
      | "crm_entry" | "private_note" | "time_entry"
  title: str                     # "Draft: Demand Letter"
  preview: str                   # one-line grounding in the transcript
  confidence: float
  confidence_reason: str | null  # "Explicitly stated" | "Inferred from context"
  source_segment_id: uuid | null # for "View source" jump-to-transcript in the UI
  extracted_fields: json         # type-specific, e.g. parties/dates/facts
  pre_checked: bool               # whether the tray shows it selected by default
  status: "detected" | "generated" | "dismissed" | "error"
```

`extracted_fields` shape by type:
- `draft_document`: `{document_kind, parties, key_facts}`
- `calendar_event`: `{title, date, time}`
- `workspace_matter`: `{matter_name, client, existing_matter_id?}` — the
  detector fills `existing_matter_id` itself when it recognizes a known
  client; the executor links to that `Matter` instead of creating a new one.
- `crm_entry`: `{contact_name, updates}`
- `private_note`: `{note_text}`
- `time_entry`: `{duration_hours, activity_description, matter_name}`

## 4. API surface (backend, agent-agnostic)

| Method | Path | Purpose |
|---|---|---|
| POST | `/sessions` | Create a session (`source`, `title`, `language_hint`) |
| WS | `/sessions/{id}/stream` | Client streams audio chunks; server pushes back partial `TranscriptSegment`s as they're transcribed |
| POST | `/webhooks/omi` | Omi pushes transcript segments here; verify shared-secret header |
| GET | `/sessions/{id}` | Session status + transcript + detected actions + flagged moments |
| GET | `/sessions` | List sessions (for the Lovable dashboard) |
| POST | `/sessions/{id}/finalize` | Lock the session, mark `ready` |
| POST | `/sessions/{id}/flags` | Drop a flagged moment (`at_ms`, optional `label`) — call the instant the user taps Flag, not on Stop |
| POST | `/sessions/{id}/speakers` | Body `{"mapping": {"Speaker 1": "John Kamau"}}` — relabel diarization labels to real names. Call after Stop, before `/detect` |
| PATCH | `/sessions/{id}/segments/{segment_id}` | Body `{"redacted": true\|false}` — mark/unmark a segment privileged so `/detect` excludes it |
| POST | `/sessions/{id}/detect` | Run the detection pass (excludes redacted segments, weighs flags, checks known matters); returns the action tray |
| GET | `/sessions/{id}/actions` | Re-fetch the current action tray for this session |
| POST | `/sessions/{id}/generate` | Body `{"action_ids": [...]}`. Executes each selected action, returns `list[ActionResult]` |
| GET | `/matters` | List known client/matter records (for the frontend to show "known clients", if useful) |
| POST | `/matters` | Manually create a matter (e.g. to pre-seed existing clients) |

`/internal/detect` and `/internal/generate` also exist (see §8) but are
called by the deployed Trigger.dev tasks, not the frontend — omitted
from this table since Lovable never calls them directly.

**Order matters for one flow:** relabel speakers and apply redactions
*before* calling `/detect` — both feed directly into the prompt.

## 5. Build order

1. **Data model + Supabase tables** — `Session`, `TranscriptSegment`,
   `DetectedAction`, `FlaggedMoment`, `Matter`.
2. **`/sessions` CRUD + `GET /sessions/{id}`** — nothing works without this.
3. **Omi webhook path first** — easiest end-to-end demo (no live audio).
4. **Speaker relabel + redaction endpoints** — small, high-leverage,
   needed before detection is trustworthy.
5. **Mic WebSocket path + no-look Flag button** — chunked audio in,
   Whisper out, partial segments back; flags recorded as they happen.
6. **Detection pass** (`/detect`) — the core of the product. Feed it
   flags and known matters from the start, not as an afterthought.
7. **Generation pass** (`/generate`) — draft_document, private_note,
   calendar_event, and time_entry are fully real; workspace_matter
   creates or links a real `Matter`; crm_entry stays stubbed.
8. **Lovable frontend** — once 1–7 are stable, generate the prompt for it.

## 6. Explicit non-goals for now

- Production-grade speaker diarization (best-effort labels + manual
  relabel is the answer, not automatic voice-identity recognition).
- Real auth flow beyond a shared secret / Supabase session token passthrough.
- Multi-tenant session isolation beyond a `user_id` column.
- Handling Omi's raw audio path (if your Omi app is configured for
  transcript webhooks, don't also build raw-audio ingestion for it).
- Real CRM contact creation is best-effort against an unconfirmed
  endpoint path (see §8) — confirm against Ambiguous's live API
  reference before depending on it for a real demo.
- Fuzzy/ML matter matching — `find_matter_by_client` is a simple
  case-insensitive substring match; good enough for a demo, not for
  production client-matching.

## 8. Sponsor integrations

Built to genuinely use rather than checkbox these — each degrades
gracefully to local-only behavior if its key isn't set, so the whole
pipeline works with zero sponsor credentials configured and upgrades
automatically as keys are added.

- **OpenAI + OpenRouter** — `DETECTION_MODEL`/`DRAFTING_MODEL` default
  to `openai/gpt-4o`, routed through OpenRouter (`action_detector.py`,
  `action_executor.py`). `ASR_PROVIDER` defaults to OpenRouter Whisper
  (`openai/whisper-large-v3` via `/api/v1/audio/transcriptions` in
  `transcription.py`), so live captions share the same key. Direct
  OpenAI or Groq Whisper remain available by switching `ASR_PROVIDER`.
- **Ambiguous AI** (`app/integrations/ambiguous_client.py`) — real REST
  calls into a live Ambiguous workspace: `POST /api/documents` for
  draft_document, `POST /api/calendar/events` for calendar_event,
  `POST /api/crm/deals` (+ `PATCH .../:id` for linking) for
  workspace_matter, and a best-effort `POST /api/crm/contacts` for
  crm_entry. After a document lands, `POST /api/channels/:id/messages`
  notifies a human it's ready for review — this is a deliberate choice:
  never auto-send substantive legal content (e.g. via Mail) without a
  person in the loop. Every function no-ops if `AMBIGUOUS_API_KEY` isn't
  set. The CRM contacts route follows the module's CRUD convention but
  wasn't explicitly listed in Ambiguous's public API reference — confirm
  the exact path against their live Scalar docs before relying on it.
- **Trigger.dev** (`app/services/trigger_client.py` +
  the sibling `trigger/` TypeScript project) — `/sessions/{id}/detect`
  and `/generate` prefer running as Trigger.dev background tasks
  (`detect-actions`, `generate-actions`) for retries and observability,
  falling back to calling `action_detector.py`/`action_executor.py`
  directly in-process if `TRIGGER_SECRET_KEY` isn't set. The Trigger.dev
  tasks themselves are thin relays into this backend's `/internal/detect`
  and `/internal/generate` endpoints (protected by
  `BACKEND_INTERNAL_SECRET`) — all real logic stays in one place
  (Python), never duplicated into TypeScript. **Requires
  `BACKEND_INTERNAL_URL` to be a publicly reachable URL** when using
  real Trigger.dev — `localhost` won't work since their cloud calls it.
  See `trigger/README.md`.
- **Exa** (`app/integrations/exa_client.py`, orchestrated by
  `app/services/enrichment.py`) — after detection, looks up any named
  counterparty/company via Exa's company-search category and attaches
  the result as `extracted_fields.background_info` on the relevant card.
  Purely a sanity-check reference for the user, never fed back into
  drafted legal text. No-ops if `EXA_API_KEY` isn't set.

## 9. Open decisions you'll need to make live

- Which Whisper endpoint (OpenAI's is the default for sponsor alignment
  and code-switched Swahili/English accuracy; Groq's is faster and
  cheaper if latency matters more during the live demo).
- How aggressively to pre-check `time_entry` actions by default — some
  lawyers want every session auto-logged, others want to opt in every time.
- Whether to actually deploy the Trigger.dev tasks for the demo (needs a
  publicly reachable backend URL) or rely on the in-process fallback —
  the fallback is functionally identical, just without the dashboard
  observability and automatic retries.
