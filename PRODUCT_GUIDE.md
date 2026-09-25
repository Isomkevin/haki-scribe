# HakiScribe Product Guide

## Purpose

HakiScribe is HakiChain's listening instrument for legal work. It is designed for lawyers, judges, clerks, and legal-aid teams whose work begins in spoken conversations: client meetings, court hearings, chambers discussions, voice notes, and wearable-captured sessions.

Its central promise is that a recording is not the end product. HakiScribe converts a reviewed conversation into selectable, source-grounded legal work while keeping a human professional responsible for every consequential decision.

## The user journey

1. A user signs in and starts a new workspace session.
2. They capture speech through a browser microphone, an Omi wearable transcript webhook, or a prepared demo session.
3. Live captions show that the system is listening. A large **Flag this moment** control lets the user bookmark important moments without interrupting the conversation.
4. When recording stops, the user reviews the transcript, gives speakers meaningful names, and marks privileged or off-record content.
5. HakiScribe excludes redacted content from later AI processing and analyses the remaining transcript.
6. The Action Tray presents suggested work. The user selects only the actions they want.
7. HakiScribe generates editable outputs, such as a draft letter or calendar event, and can deliver supported outputs to connected tools.
8. The completed session remains available in the library as a record of work, not simply a recording archive.

## What the product does today

### Capture and transcription

- Records audio in the browser and streams chunks to the FastAPI backend through WebSockets.
- Accepts Omi Miniapp pairing and legacy transcript-webhook flows.
- Supports English, Kiswahili, and configured African code-switching modes.
- Uses OpenRouter Whisper by default for live captions; Groq Whisper, direct OpenAI Whisper, and Intron Sahara can be selected where their credentials are configured.
- Supports Intron Sahara legal/court-hearing refinement after recording for multilingual and code-switch sessions.
- Provides a completed judge/demo path so the product can be evaluated without a microphone.

### In-room controls and legal safeguards

- **Flag this moment** creates a timestamped bookmark that weights later action detection toward the part of a conversation the professional identified as important.
- Speaker relabeling replaces generic labels such as “Speaker 1” with meaningful names before drafting.
- Privilege/off-record redaction keeps the line visible to the reviewer but excludes it from detection and generation.
- Action cards show confidence, whether an item was explicitly stated or inferred, and a source link back to the relevant transcript segment.
- Generated outputs remain editable and are never automatically sent as legal advice.

### The Action Tray

After analysis, HakiScribe can propose the following types of work:

| Action | What it creates or updates |
| --- | --- |
| Draft document | An editable letter, brief, memo, or other legal draft |
| Calendar event | A follow-up or hearing event, including an `.ics` representation |
| Workspace matter | A new matter or a link to an existing matter |
| CRM entry | A best-effort contact or relationship update |
| Time entry | A billable-time record |
| Private note | An internal note tied to the session |

The system uses two separate AI stages: a detection pass proposes possible work; a type-specific generation pass performs work only for the actions the user selected.

### Case, research, and workspace experience

- A private session library lets users reopen prior work.
- The matter tracker supports a persistent client/matter registry.
- The research area can use Exa for company background, citation crawling, and news monitoring.
- Exa content is contextual reference only; it is not silently inserted into legal drafts as fact.
- Public landing, login, new-session, session, tracker, research, settings, and connector routes are separated.
- The interface is mobile-first for capture and desktop-friendly for careful review and editing.

### Integrations and delivery

- **Ambiguous AI:** supported delivery for documents, calendar events, CRM deals, and review notifications; calls safely no-op when unconfigured.
- **Trigger.dev:** durable background execution for detect, generate, and research tasks, with an in-process fallback.
- **Google Drive, Google Calendar, Dropbox, OneDrive:** OAuth connectors are implemented in the product.
- **Gemini, Anthropic, OpenAI:** connector flows support Vertex OAuth or verified API keys where applicable.
- **WhatsApp:** supports a human-review handoff path rather than automatic substantive delivery.

### Architecture and storage

- Frontend: React 19, TanStack Start, Vite, and Tailwind CSS.
- Backend: FastAPI, WebSockets, and a session/transcript/action data model.
- Storage: in-memory/local JSON for development, with optional Postgres through `DATABASE_URL` and optional S3 draft archiving.
- Deployment: Render Blueprint with a Lovable-hosted frontend.
- Core records include sessions, transcript segments, flagged moments, detected actions, and matters. Transcript segments preserve source metadata for auditability.

## Trust, safety, and data handling

- The product asks for browser microphone permission before capture.
- Privileged segments are deliberately excluded before language-model detection and generation.
- HakiScribe does not treat generated text as a final legal conclusion; the professional selects, reviews, and edits it.
- Full recording uploads used for Sahara refinement are processed for transcription and are not intended to be durably archived by default.
- API keys are stored server-side or in connector storage and are masked in the UI.
- The product is working toward Kenya Data Protection Act alignment; it does not claim completed certification.

## Implemented but dependent on external configuration

These flows are in the codebase but need workspace-owner configuration before they are production-ready:

- Register Google, Dropbox, and Microsoft OAuth applications; set their client IDs/secrets in Render.
- Confirm deployed Render is on the latest backend commit and configure `AUTH_SECRET`, `HAKISCRIBE_USERS`, and production demo-account settings.
- Configure real provider keys for OpenRouter, Intron Sahara, Trigger.dev, Exa, Ambiguous AI, and any chosen third-party ASR provider.
- Configure a public `BACKEND_INTERNAL_URL` and `BACKEND_INTERNAL_SECRET` when using Trigger.dev cloud tasks.
- Verify Ambiguous AI's live CRM-contact endpoint before relying on contact creation in production.

## Work still to implement

### Highest-priority production work

1. **Multi-tenant security and per-lawyer vaults.** Signed-in users currently share one workspace/case library. Production must isolate firms, lawyers, clients, permissions, and records.
2. **Recording-consent workflow.** Add an explicit in-product confirmation that all participants consented to recording, with jurisdiction-aware policy and an audit trail.
3. **Retention, deletion, and data-governance controls.** Define retention periods, deletion/export workflows, processor agreements, and data-residency decisions.
4. **Production-grade identity and access management.** Add account lifecycle management, password/security controls, role-based access, session hardening, audit logs, and secure secret rotation.
5. **Robust matter matching.** Replace case-insensitive substring matching with reviewed, explainable entity and matter resolution.

### Product and AI improvements

- Production-grade speaker diarization and optional, consent-based voice identity support; manual relabeling remains the current safeguard.
- Broader evaluation of code-switch ASR using consented, de-identified legal audio and reproducible model comparisons.
- Stronger legal-entity extraction for party names, case references, monetary amounts, dates, and court venues.
- Better controls for which action types are pre-selected, especially billable time entries.
- More legal-document templates, jurisdiction-specific drafting rules, and configurable firm style guides.
- Better failure visibility, retry history, operational dashboards, and provider cost/latency telemetry.
- Accessibility testing and support for additional African languages and local legal terminology.

### Integration and operational work

- Complete OAuth provider registration and end-to-end production testing.
- Confirm all delivery APIs against their live documentation and add contract tests.
- Add monitoring, backup/recovery procedures, rate limits, abuse controls, and incident-response runbooks.
- Add database migrations, test fixtures, automated integration tests, and release checks.
- Establish a formal privacy, security, and legal-review program before use with real privileged matter data.

## Explicit non-goals today

- Automatic voice-identity recognition is not a current feature.
- Raw-audio ingestion from Omi is not planned when using the transcript-webhook path.
- The product is not yet a full multi-tenant practice-management system.
- It does not automatically send legal advice or client-facing substantive work.
- It does not claim full regulatory certification or production readiness for sensitive legal deployments.

## Documentation map

| Document | Use |
| --- | --- |
| [README.md](./README.md) | Product story, routes, stack, local run instructions |
| [SPEC.md](./SPEC.md) | Architecture, API surface, data model, explicit non-goals |
| [roadmap.md](./roadmap.md) | Completed work and external deployment setup |
| [hakiscribe-backend/README.md](./hakiscribe-backend/README.md) | Backend/API operations |
| [docs/CONNECTOR_OAUTH_SETUP.md](./docs/CONNECTOR_OAUTH_SETUP.md) | OAuth deployment setup |
| [Sahara submission packet](./Sahara_CodeSwitch_Africa_Challenge_submission/README.md) | Code-switching benchmark and challenge materials |

## Product principle

HakiScribe is not intended to replace legal judgment. It makes spoken work usable: capture what was said, preserve what must stay private, show the professional why an action was suggested, and leave the final decision with the person accountable for it.
