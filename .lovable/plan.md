# Connectors page for HakiScribe

A new "Connectors" page where a lawyer links HakiScribe to the other tools they use — AI assistants (Claude, Legora, Harvey), cloud storage (Google Drive, Dropbox, OneDrive), and the HakiChain suite — so drafted documents, research and calendar events can flow to where their practice already lives.

## What the user sees

- A "Connectors" entry next to "Case tracker" on the home screen, and in the tracker header.
- `/connectors` page: grouped cards — **AI assistants** (Claude, Legora, Harvey, Ambiguous), **Storage** (Google Drive, Dropbox, OneDrive), **Practice suite** (HakiChain, Kenya Law). Each card shows the tool's name, what it does with HakiScribe ("Send drafted documents", "Run research through Claude", "Archive to your firm drive"), a Connect button, and once linked a "Connected" status, the connected-at date, and Disconnect.
- Connecting opens a small form asking for the credential that tool needs — an API key for Claude/Legora/Harvey, an access token for Drive/Dropbox, a HakiChain API token — with a one-line note on where to get it and a "Stored on the server, never in the browser" trust line.
- Where a connection unlocks behaviour, it's used automatically: drafted documents offer "Send to Google Drive / Dropbox", research can run "with Claude", and HakiChain-linked sessions can sync matters.

## Backend work

- New `integrations` service (`hakiscribe-backend/app/services/integrations.py`): registry of supported providers (id, name, group, credential fields, help text), each provider module with `verify()` (a harmless API call to confirm the credential works) and `export_document()` / `run()` where applicable.
- Persist connections as a new `haki_records` kind `"integrations"` in the existing database layer (`db.py`) so they survive restarts once `DATABASE_URL` is set; falls back to the snapshot file meanwhile. Credentials stored server-side only — never returned in full by the API (masked, e.g. `sk-…9f2`).
- Routes: `GET /integrations` (list with status), `POST /integrations/{provider}` (connect + verify), `DELETE /integrations/{provider}` (disconnect).
- Export actions: `POST /sessions/{id}/documents/{action_id}/export` targeting a connected storage provider — pushes the drafted document text as a `.docx`-style file to Drive/Dropbox and records the destination link on the result.
- Bring-your-own LLM keys: any connected model provider — Anthropic (Claude), OpenAI, Google Gemini, Mistral, OpenRouter, or a custom OpenAI-compatible endpoint — is added to the "Ask an AI model" picker alongside the built-in default, with `llm_client` routing the task through that provider's key.

## Frontend work

- `src/routes/connectors.tsx` + `src/components/hakiscribe/connectors.tsx` — page with grouped provider cards, connect dialog, status badges, masked credential display, disconnect with confirm.
- `src/lib/hakiscribe.ts` — `Integration` type, `listIntegrations()`, `connectIntegration()`, `disconnectIntegration()`, `exportDocument()`.
- Result cards for drafted documents gain an "Export" menu listing connected storage providers; the Ask composer offers "Claude" as a model choice when connected.
- Mobile-first, same HakiChain palette and restrained card styling as the tracker.

## Notes

- Real verification only: a connector shows "Connected" only after the provider's API confirms the credential works; failures surface the provider's own error.
- Google Drive/Dropbox full OAuth consent screens are a later upgrade; v1 uses a user-provided token so it works immediately without app registrations.
- No invented behaviour: providers a user hasn't connected simply show "Not connected"; nothing is faked.
