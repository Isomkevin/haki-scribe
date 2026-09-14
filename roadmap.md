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

## External setup

- [x] Set `VITE_API_BASE_URL` to the deployed FastAPI URL (`https://hakiscribe-backend.onrender.com`).
- [ ] Register the OAuth apps and add their credentials on Render (`GOOGLE_OAUTH_CLIENT_ID`/`SECRET`, `DROPBOX_APP_KEY`/`SECRET`, `MICROSOFT_CLIENT_ID`/`SECRET`), using the callback `https://hakiscribe-backend.onrender.com/integrations/oauth/{provider}/callback`. Guide: [`docs/CONNECTOR_OAUTH_SETUP.md`](./docs/CONNECTOR_OAUTH_SETUP.md). Blocked: only you can create those apps.
- [ ] Deploy the updated backend to Render so the connector sign-in endpoints exist. Blocked: deployment happens from your Render account.
- [ ] Add `AUTH_SECRET` and your real `HAKISCRIBE_USERS` accounts on Render, and set `DEMO_LOGIN_ENABLED=false` before any real client work. Blocked: only you can choose those accounts.
