# Split the landing page from private session work

## Goal

Turn `/` into a public landing page with information sections only. Move session creation and the past-session library to `/new`, while keeping recording and every subsequent step inside the separate `/sessions/$sessionId` workspace. No private transcript, client title, generated document, or session result appears on the landing page.

## Changes

### Landing page (`/`)

- Keep the hero ("Capture what matters. Leave with work ready."), the three practice steps, the environments strip, and the trust line as the landing content.
- Remove the "Start a session" card from the hero grid; the hero becomes single-column on all screens.
- Add a primary "Start a session" button linking to `/new`. Keep the completed judge demo inside the private `/new` area rather than exposing a session workspace from the landing.
- Do not show live library counts, client session titles, matters, documents, transcripts, or results on the landing. Use non-sensitive product information instead.
- Expand the public information sections so the landing page stands alone: how HakiScribe works, where it is used, the artifact and automation features it supports, source traceability, connector capabilities, and the privacy promise.
- Give the landing page a polished, top-tier presentation while preserving the existing restrained HakiChain visual language.

### Private session start (`/new`)

- Add `src/routes/new.tsx` with its own head metadata ("Start a session — HakiScribe").
- Move the whole session-creation card there: title, Microphone/Omi source control, language hint, Start recording / Start listening action, and the completed judge demo button.
- Move the past-sessions library (session rows, matters, sync-restore action, connection error and empty states) there too, since it reveals client work and belongs with the private area.
- Use the existing `PageShell` with a back link to the landing, so public information and private work stay clearly separate.
- Creation still navigates into `/sessions/$sessionId` exactly as today.

### Private recording and post-recording workspace (`/sessions/$sessionId`)

- Keep recording on the session-specific route, never embedded in `/` or `/new`.
- Keep every step after recording on that same separate workspace: speaker relabelling, privileged/off-record review, transcript skim, analysis, action tray, artifact selection, generation, and results.
- Existing sessions reopen directly into their correct private workspace state.
- Do not surface transcript content, flags, speaker names, generated artifacts, connector results, or session actions anywhere on the public landing page.

### Plumbing

- `src/components/hakiscribe/app.tsx` — split `HomePage` into `LandingPage` (used by `src/routes/index.tsx`) and `NewSessionPage` (used by the new route); shared private pieces such as `SessionRow`, `LibraryMatters`, stats, and showcase actions remain with the private page/workspace.
- `src/routes/index.tsx` — render `LandingPage`; update its existing metadata to describe the public product landing only.
- `src/routes/sessions.$sessionId.tsx` remains the sole route for recording and all post-recording work, with session-specific metadata that does not expose private content.
- `PageShell` brand/home links keep pointing to `/` (the landing).
- No backend changes, API changes, or workflow changes — only the frontend separation and landing-page presentation change.

## Validation

- Typecheck passes.
- Preview `/`: landing shows polished product information and the `/new` CTA, with no session form, demo opener, private counts, client titles, transcript details, or results.
- Preview `/new`: session form and completed demo work; the library lists sessions; creating a session opens `/sessions/$sessionId`.
- Preview `/sessions/$sessionId`: recording, speaker review, redaction, analysis, action tray, generation, and results all remain in the private workspace.
- Check phone and desktop widths for all three route states, including direct navigation and back links.
