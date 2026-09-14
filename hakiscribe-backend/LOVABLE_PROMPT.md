Build a mobile-first web app called **HakiScribe** — a legal work
companion that records conversations (client meetings, court
proceedings) and turns them into a tray of ready-to-generate legal
artifacts, not just a transcript.

## Product framing (important — read before building)

This is NOT a transcription app with a transcript viewer. The
transcript is a means, not the deliverable. The core interaction is:
record (with the ability to flag important moments hands-free) →
relabel speakers → the app analyzes what was said → it shows a tray of
concrete, individually-selectable, source-traceable legal artifacts it
detected → the user picks which ones they want → the app generates
them. Think Granola's "AI notes" reveal, but the output is legal work
product, not meeting notes — and every claim it makes has to be
verifiable against the actual transcript, because a legal professional
is liable for what gets generated.

Design for legal professionals broadly — lawyers, judges, clerks — not
one specific role. Mobile is the primary surface (used in courtrooms
and client meetings, hands often not free), but it needs to work well
on desktop too, where review/editing happens.

## Visual direction

Trustworthy and precise, not "AI startup generic." Avoid purple gradients,
glowing orbs, or anything that reads as a demo toy — this handles real
legal work, often privileged. Lean toward: a restrained, mostly-neutral
palette (deep navy or charcoal as the anchor, one warm accent used
sparingly for primary actions), a serif or high-legibility sans for
document/transcript text (this is legal reading material), clean sans
for UI chrome, generous whitespace, subtle borders over heavy shadows.
Confidence and calm, not excitement. A small, persistent trust line
("Not used to train models · GDPR compliant") should be visible during
recording and on the action tray — for this audience, that line is why
they trust the tool at all, not decoration.

## Screens

### 1. Home / New Session
- Minimal. A record button (large, unmistakable) and a source toggle:
  **Mic** or **Omi wearable**. No document-type picker — that's the
  whole point, don't add one.
- Below the fold: a list of past sessions (see Session Library below),
  so this doubles as the dashboard.

### 2. Recording
- Full-screen, unambiguous "recording" state: elapsed time, a live
  waveform or pulse animation.
- A large, thumb-reachable **"Flag this moment"** button — designed to
  be tappable without looking at the screen, mid-conversation. Each tap
  drops a timestamped chip in a horizontal scroll row above the
  waveform (e.g. "09:12 · Contract terms"). This is a first-class
  control, not a minor extra — it's how a lawyer marks "this mattered"
  without breaking eye contact with their client.
  Calls `POST /sessions/{id}/flags` with `{"at_ms": ..., "label"?: ...}`
  on every tap.
- Live captions scroll in small, muted italic text below — they prove
  it's working but are secondary, not the headline.
- Live captions come from the WebSocket (see API contract) when source
  is Mic. When source is Omi, show a "listening via Omi" state instead
  (Omi transcribes on its own and pushes segments via webhook — no
  client-side audio capture needed for that path).
- A clear Stop button.

### 3. Speaker check (new, brief — appears right after Stop)
- A short screen listing each distinct raw speaker label found in the
  transcript (e.g. "Speaker 1", "Speaker 2") with a text field next to
  each to type the real name. Pre-fill nothing — force a deliberate
  entry, since this feeds directly into generated documents. A "Skip"
  option is fine (keeps raw labels), but don't skip past this silently.
- On submit, `POST /sessions/{id}/speakers` with
  `{"mapping": {"Speaker 1": "John Kamau", ...}}`.

### 4. Review & redact (new, brief — appears right after speaker check)
- The full transcript as a simple scrollable list of speaker-labeled
  lines. Each line has a small toggle (e.g. a lock icon) to mark it
  privileged/off-record. Toggling calls
  `PATCH /sessions/{id}/segments/{segment_id}` with `{"redacted": true|false}`.
- Redacted lines stay visible but visually muted/struck-through, with a
  small "won't be used" label — the user should always be able to see
  and reverse what they've excluded, never have it silently vanish.
- A single "Continue" button moves to analysis. This screen should feel
  like a 10-second skim, not a chore — most sessions have zero redactions.

### 5. Analyzing (transition state)
- Brief, calm loading state — "Reviewing what happened..." Not a
  generic spinner; something that feels like careful reading, not
  frantic processing.
- Calls `POST /sessions/{id}/finalize` then `POST /sessions/{id}/detect`
  in sequence, then transitions to the Action Tray.

### 6. Action Tray (the core screen)
- A vertical list of cards, one per detected action. Each card shows:
  - An icon distinguishing the type (document / calendar / briefcase for
    matter / contact for CRM / clock for time entry / note)
  - Title (e.g. "Draft: Demand Letter")
  - One-line preview grounding it in what was said
  - A checkbox — pre-checked or unchecked per the `pre_checked` field
    from the API, all editable
  - A footer row with the `confidence_reason` as a short tag
    ("Explicitly stated" / "Inferred from context") and a **"View
    source"** link that jumps to (or expands inline) the transcript line
    at `source_segment_id` — this is not optional polish, it's the thing
    that makes a legal professional trust an individual card enough to
    check it
  - Lower-confidence / speculative cards render visually muted and start
    unchecked (see the design reference — the "new matter" card is a
    good example of this treatment)
- Tapping a card expands it to show its `extracted_fields` in a simple
  editable form (e.g. for a calendar event: title, date, time — all
  editable before generating).
- A **"Generate all high-confidence"** shortcut sits above the list —
  one tap selects every card with `pre_checked: true` without requiring
  the user to review each one individually; they can still deselect
  before generating. Below the list, a sticky "Generate selected (N)"
  button, N = count of checked cards, disabled at zero.
- Calls `POST /sessions/{id}/generate` with the selected `action_ids`.

### 7. Results
- Each generated action becomes a result card:
  - `draft_document` → shows the generated text in a document-styled
    reader (serif, generous line height, looks like a real legal doc,
    not a chat bubble), with copy/export affordances, and stays
    editable inline — never present it as a locked final artifact,
    lawyers will always want to edit before it leaves the app.
  - `calendar_event` → shows the event details with a "download .ics /
    add to calendar" action (the API returns real .ics content).
  - `time_entry` → shows duration, activity description, and which
    matter it's billed to, styled like a timesheet line item.
  - `private_note` → shown inline as a saved note.
  - `workspace_matter` → if the result's `note` says "linked to existing
    matter", show it as "Added to existing matter: {matter_name}"; if it
    says a new matter was created, show "New matter opened: {matter_name}".
  - `crm_entry` → shown as a generic confirmation card ("Contact
    updated: ...") — this is a backend stub today, so render whatever
    `result` object comes back generically (key/value), don't assume
    fields beyond what's documented below.
- Any action that comes back with `status: "error"` shows a quiet inline
  error on that card only — never blocks the rest of the results.

### 8. Session Library / Session Detail
- List view: each past session as a row/card showing title, date,
  source (mic/Omi icon), status, and small badges for what got
  generated from it (icons matching the action types that reached
  `generated` status).
- Detail view: reopens the Action Tray + Results state for that session
  (fetch via `GET /sessions/{id}` which includes `detected_actions` and
  `flagged_moments`), so nothing is a dead end — everything's reviewable
  later.

## API contract

Base URL: configurable via an environment variable (`VITE_API_BASE_URL`
or equivalent) — don't hardcode a host, the backend URL isn't final yet.

```
POST   /sessions
  body: { "title": string, "source": "mic" | "omi", "language_hint"?: string }
  returns: Session

GET    /sessions
  returns: Session[]

GET    /sessions/{id}
  returns: Session & { transcript: TranscriptSegment[], detected_actions: DetectedAction[], flagged_moments: FlaggedMoment[] }

WS     /sessions/{id}/stream
  client sends: raw audio chunk bytes (binary frames, ~2-3s each)
  server sends back: TranscriptSegment (JSON) per chunk

POST   /webhooks/omi        (backend-to-backend, frontend doesn't call this)

POST   /sessions/{id}/finalize
  returns: Session (status becomes "ready")

POST   /sessions/{id}/flags
  body: { "at_ms": number, "label"?: string }
  returns: FlaggedMoment

POST   /sessions/{id}/speakers
  body: { "mapping": { [rawLabel: string]: string } }
  returns: TranscriptSegment[]   (the full updated transcript)

PATCH  /sessions/{id}/segments/{segment_id}
  body: { "redacted": boolean }
  returns: TranscriptSegment

POST   /sessions/{id}/detect
  returns: DetectedAction[]

GET    /sessions/{id}/actions
  returns: DetectedAction[]

POST   /sessions/{id}/generate
  body: { "action_ids": string[] }
  returns: ActionResult[]

GET    /matters
  returns: Matter[]
```

```ts
type Session = {
  id: string
  title: string
  source: "mic" | "omi"
  language_hint: string | null
  status: "recording" | "processing" | "ready" | "exported"
  created_at: string
  updated_at: string
}

type TranscriptSegment = {
  id: string
  session_id: string
  speaker: string | null
  text: string
  start_ms: number
  end_ms: number
  confidence: number | null
  redacted: boolean
}

type FlaggedMoment = {
  id: string
  session_id: string
  at_ms: number
  label: string | null
}

type Matter = {
  id: string
  client_name: string
  matter_name: string
  created_at: string
}

type DetectedAction = {
  id: string
  session_id: string
  type: "draft_document" | "calendar_event" | "workspace_matter" | "crm_entry" | "private_note" | "time_entry"
  title: string
  preview: string
  confidence: number
  confidence_reason: string | null       // "Explicitly stated" | "Inferred from context"
  source_segment_id: string | null       // drives the "View source" link
  extracted_fields: Record<string, any>  // shape varies by type, see below
  pre_checked: boolean
  status: "detected" | "generated" | "dismissed" | "error"
}

type ActionResult = {
  action_id: string
  type: DetectedAction["type"]
  status: "success" | "error"
  result: Record<string, any>   // shape varies by type, see below
  error: string | null
}
```

`extracted_fields` / `result` shapes by type (render generically —
these are the common fields, but don't hard-fail on missing ones):

- `draft_document`: fields `{ document_kind, parties, key_facts }` →
  result `{ document_text, document_kind }`
- `calendar_event`: fields `{ title, date, time }` → result
  `{ title, start, ics }` (`ics` is raw .ics file content as a string —
  build a download link from it, e.g. a `data:text/calendar` URI)
- `workspace_matter`: fields `{ matter_name, client, existing_matter_id?
  }` → result `{ matter_id, matter_name, note }` (`note` tells you
  whether it was linked to an existing matter or a new one was created —
  see Results screen above)
- `crm_entry`: fields `{ contact_name, updates }` → result
  `{ contact_id, contact_name, note }`
- `private_note`: fields `{ note_text }` → result `{ note_text }`
- `time_entry`: fields `{ duration_hours, activity_description,
  matter_name }` → result `{ duration_hours, activity_description,
  matter_name, billable }`

## State handling notes

- Session flow is a state machine driven by `Session.status` plus where
  the user is in the post-recording sequence: `recording` → (stop) →
  speaker check → review & redact → `processing`/`ready` with no
  actions yet → (detect completes) → tray shown → (generate completes)
  → results shown. Reopening an old session should be able to resume at
  whatever state it's actually in — don't assume every session was just
  recorded, and don't force a completed session back through speaker
  check or redaction.
- Mic audio capture: use the browser's MediaRecorder/Web Audio API,
  chunk into ~2-3 second segments, send each as a binary WebSocket
  frame. Show each returned `TranscriptSegment` appended to the live
  caption feed immediately.
- Handle the WebSocket disconnecting gracefully (e.g. on Stop) — closing
  it is expected, not an error state.
- This is a real product handling real legal conversations — no fake
  placeholder data once wired up. If the backend isn't reachable, show
  a clear connection error, not silently-empty screens.
