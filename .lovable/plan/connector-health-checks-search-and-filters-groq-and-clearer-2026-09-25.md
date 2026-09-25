# Connector health checks, search and filters, Groq, and clearer sign-in errors

## What you'll see

- **Live status on every connector card**, not only "Connected". Each card shows one of these:
  - **Valid** (green): checked just now, and the provider accepted the key or sign-in.
  - **Expired** (amber): the sign-in has lapsed. A "Sign in again" button appears.
  - **Invalid** (red): the provider rejected the key. The card shows the provider's own reason.
  - **Not connected** (grey).
  - **Checking…** while the check runs.
  
  Each card also shows when it was last checked and has a "Check again" button.
- **A health summary at the top of the page**, for example "5 connected · 4 valid · 1 needs attention". It also has a "Check all" button.
- **Search and filters.** A search box matches connector names and descriptions. Filter chips cover All, AI assistants, Storage, Practice suite and Needs attention. A status dropdown filters by Valid, Expired, Invalid or Not connected. Your choices are kept in the page address, so a refresh keeps them.
- **Groq as a new AI connector.** It connects automatically from the `GROQ_API_KEY` you already set on Render, and shows the "Workspace key" badge. You can also paste your own key. Groq models (Llama 3.3 70B, Llama 3.1 8B) appear in the Ask model picker.
- **Plain-language sign-in errors.** When a Google, Dropbox or Microsoft sign-in fails, cancels or expires, the popup and a notice on the page explain what happened and what to do. Examples:
  - "You cancelled the Google sign-in. Nothing was changed."
  - "Google sign-in isn't set up on the server yet. Ask your administrator to add it."
  - "This sign-in link expired. Start again."
  - "Your Dropbox access expired. Sign in again to keep exporting."
  
  If you try to export while a sign-in has expired, you get the same guidance and a "Reconnect" link, instead of a raw error.

## Technical details

**Backend (`hakiscribe-backend`)**
- `integrations.py`:
  - Add a `groq` provider (group ai, field `api_key`) and add `groq: {"api_key": "GROQ_API_KEY"}` to the env map.
  - Add `_verify_groq`, which calls `GET https://api.groq.com/openai/v1/models`.
  - `connected_llm_models` adds `groq:llama-3.3-70b-versatile` and `groq:llama-3.1-8b-instant`.
  - Completion goes through Groq's OpenAI-compatible chat endpoint.
- New `check_health(provider_id)`:
  - Loads the saved credentials through `get_fresh_creds`, which refreshes OAuth tokens, then runs `verify`.
  - Sorts the result into `valid`, `expired`, `invalid`, `unreachable` or `not_connected`:
    - `invalid_grant` or a failed refresh counts as expired.
    - 401 or 403 counts as invalid.
    - A timeout or 5xx counts as unreachable.
  - Stores `last_checked_at`, `health` and `health_error` on the connection record.
- Routes:
  - `GET /integrations/health` checks all providers in parallel with a timeout for each.
  - `POST /integrations/{id}/check` checks one provider.
  - Both are declared before `/{provider_id}`.
  - `list_connections` includes the last saved health.
- OAuth callback (`routers/integrations.py` and `oauth.py`):
  - Map error codes to friendly titles and next steps: `access_denied`, bad or expired state, `redirect_uri_mismatch`, `invalid_client`, provider not configured, missing refresh token, token exchange failure.
  - The popup page shows a "What to do" line.
  - The `postMessage` carries `{status, reason, message}`.
- Export and calendar routes: an expired or refresh failure returns 401 with `{code: "reauth_required", provider}`.

**Frontend**
- `src/lib/hakiscribe.ts`:
  - Add a `ConnectorHealth` type, `checkAllIntegrations()` and `checkIntegration(id)`.
  - `startIntegrationOAuth` returns `{outcome, reason, message}`.
  - Add a `reauth_required` error helper.
- `connectors.tsx`:
  - Summary bar, search input, group chips, status select (search params kept in sync through `settings` route validateSearch).
  - Health badge, last-checked time and "Check again" on each card.
  - A health query runs on page load and when the window regains focus.
  - Inline notice for sign-in failures, with a retry action.
- Export menu in `app.tsx`: when the export returns `reauth_required`, show a toast with a "Reconnect" link to the connectors settings.
- Update `docs/CONNECTOR_OAUTH_SETUP.md` and `.env.example` with `GROQ_API_KEY`.

**Note:** these status checks and Groq only work after the updated backend is deployed to Render.
