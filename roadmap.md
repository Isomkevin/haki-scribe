# HakiScribe roadmap

- [x] Build the full mobile-first recording-to-artifact workflow.
- [x] Match HakiChain’s visual language.
- [x] Integrate the configured FastAPI session, transcript, detection, and generation endpoints.
- [x] Include privileged/off-record locking before analysis.
- [x] Surface Ambiguous delivery, Trigger.dev processing, OpenAI/OpenRouter generation, and Exa enrichment according to the backend response contract.
- [x] Verify mobile and desktop behavior against the live preview.
- [x] Complete the platform-wide phone, tablet, and desktop refinement pass.
- [x] Separate the public landing page from session creation and all private session work.
- [x] Add sign-in (OAuth) connections for Google Drive, Google Calendar, Dropbox and Microsoft OneDrive, with automatic token refresh and real exports.
- [x] Add a real Google sign-in for Gemini (Vertex AI) plus verified Anthropic and OpenAI key connections in the Ask-a-model picker.
- [x] Put recording, transcripts, tracker, research and settings behind a workspace sign-in, with a clearly temporary demo account for judging.
- [x] Add live connector status checks, search and filters, the Groq connector, and plain-language sign-in failure and token-expiry guidance.
- [x] Add multi-thread AI chat per session, and an Omi setup page with pairing steps, conversation import and live-transcript routing.
- [x] Add grid/list view and expandable Show more / Show less details to the Connectors page.

## External setup

- [x] Set `VITE_API_BASE_URL` to the deployed FastAPI URL (`https://hakiscribe-backend.onrender.com`).
- [ ] Register the OAuth apps and add their credentials on Render (`GOOGLE_OAUTH_CLIENT_ID`/`SECRET`, `DROPBOX_APP_KEY`/`SECRET`, `MICROSOFT_CLIENT_ID`/`SECRET`), using the callback `https://hakiscribe-backend.onrender.com/integrations/oauth/{provider}/callback`. Guide: [`docs/CONNECTOR_OAUTH_SETUP.md`](./docs/CONNECTOR_OAUTH_SETUP.md). Blocked: only you can create those apps.
- [ ] Confirm Render is on the latest commit that includes connector + auth routes, and that `AUTH_SECRET` / `HAKISCRIBE_USERS` (and optionally `DEMO_LOGIN_ENABLED=false`) are set for production. Blocked: Render dashboard access.
- [ ] Create the Omi app (Explore → Create an App → External integration), install it, and save the developer key on the Omi connector card. Blocked: your Omi account.
