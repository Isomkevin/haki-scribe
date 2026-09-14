# Split the landing page from session start

## Goal
Turn `/` into a public landing page with information sections only, and move the private session-creation area — plus the past-sessions library it reveals — to its own `/new` page. Nothing about recording, detection, or generation changes.

## Changes

### Landing page (`/`)
- Keep the hero ("Capture what matters. Leave with work ready."), the three practice steps, the environments strip, and the trust line as the landing content.
- Remove the "Start a session" card from the hero grid; the hero becomes single-column on all screens.
- Add two calls to action in place of the card: a primary "Start a session" button linking to `/new`, and a secondary "See the finished work" button that opens the completed judge demo (the existing showcase flow) so visitors can still try it from the landing.
- Keep the library-count strip as quiet landing proof points only if they read as marketing ("Sessions prepared", "Matters on the desk") — otherwise drop it from the landing. The full library moves to `/new`.
- Slightly expand the information sections so the page stands alone as a landing: how it works, where it's used, and the privacy promise.

### Private session page (`/new`)
- New route `src/routes/new.tsx` with its own head metadata ("Start a session — HakiScribe").
- Move the whole session-creation card there: title, Microphone/Omi source control, language hint, Start recording / Start listening action, and the demo button.
- Move the past-sessions library (session rows, matters, sync-restore action, connection error and empty states) there too, since it reveals client work and belongs with the private area.
- The page uses the existing `PageShell` with the back link to the landing, so the landing and the work area stay clearly separate.
- Creation still navigates into `/sessions/$sessionId` exactly as today.

### Plumbing
- `src/components/hakiscribe/app.tsx` — split `HomePage` into `LandingPage` (used by `src/routes/index.tsx`) and `NewSessionPage` (used by the new route); shared pieces (SessionRow, LibraryMatters, stats) stay in the same file.
- `src/routes/index.tsx` — render `LandingPage`; keep its existing head metadata, updated to describe the landing only.
- `PageShell` brand/home links keep pointing to `/` (the landing).
- No backend changes, no API changes, no design-system changes — same HakiChain palette and cards.

## Validation
- Typecheck passes.
- Preview `/`: landing shows hero, information sections, and CTAs — no session form, no client session titles.
- Preview `/new`: session form works (mic/omi/language), library lists sessions, creating a session still opens the session workspace.
- Check phone and desktop widths for both pages.
