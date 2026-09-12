# HakiScribe mobile-first legal companion

## Goal
Build the full HakiScribe frontend around the existing FastAPI contract, with the legal-work artifact tray as the primary outcome rather than a transcript viewer. Match the parent HakiChain product using its deep green, warm sand, ink neutrals, Inter UI type, Playfair document type, fine borders, and restrained motion.

## Product flow
1. **Home and session library**
   - Show a focused new-session area with session title, Mic/Omi segmented source control, optional language hint, and one prominent record action.
   - Fetch real past sessions from the configured API; show title, date, source, status, and generated artifact icons.
   - Display an explicit connection error when the API is unavailable. Never insert demo sessions.

2. **Recording**
   - Create a session, request microphone access only for Mic, record in 2–3 second chunks, and send binary chunks through the session WebSocket.
   - Append returned transcript segments as quiet live captions.
   - For Omi, show the dedicated “Listening via Omi” state without requesting microphone access.
   - Keep elapsed time, a stable animated waveform, live flagged-moment chips, the large no-look flag control, Stop, and the privacy trust line visible.
   - Send every flag immediately and treat an intentional WebSocket close on Stop as normal.

3. **Post-recording checks**
   - Fetch the complete session after Stop.
   - Require a deliberate speaker-name review with Save and Skip choices.
   - Show a quick transcript skim where every line can be marked privileged/off-record and restored; update each segment immediately through the API.

4. **Analysis and action tray**
   - Finalize, then detect in sequence, with a calm document-reading transition.
   - Render source-traceable action cards for all supported types, honoring `pre_checked`, confidence, and lower-confidence muted treatment.
   - Support select-all-high-confidence, individual selection, expandable editable extracted fields, and inline source transcript expansion.
   - Keep the selected-count generation action reachable at the bottom on mobile.

5. **Results and session detail**
   - Render editable legal document text, calendar details with downloadable `.ics`, time entries, private notes, matter outcomes, and generic CRM results.
   - Isolate action-level failures so successful outputs remain usable.
   - Reopen existing sessions directly into their actual tray/results state without replaying completed speaker and redaction steps.

## Technical details
- Add typed API models and a small fetch client using `VITE_API_BASE_URL`; derive `ws:`/`wss:` from the same value.
- Keep the workflow as a focused client-side state machine on `/`; use a shareable `/sessions/$sessionId` route for reopening library entries.
- Add reusable HakiScribe controls and focused screen components while retaining TanStack Start routing.
- Use the existing design-system controls and expand semantic tokens/variants rather than hardcoded colors in feature code.
- Add route-specific metadata for `/` and `/sessions/$sessionId`, plus the HakiChain font links in the document head.
- Provide accessible labels, keyboard focus, reduced-motion behavior, stable mobile dimensions, and desktop review layouts.

## Validation
- Verify compilation through the automatic harness.
- Exercise the home and unavailable-backend state in the live preview.
- Verify mobile and desktop screenshots for clipping, overlap, readable action cards, reachable controls, and correct HakiChain styling.
- Where a live backend is available through `VITE_API_BASE_URL`, exercise session loading; otherwise retain honest connection messaging rather than mock data.
