# Real LLM connections + a private login

## One thing to know first

Two of the three platforms you named do not offer a "Sign in with…" flow for API access:

- **Anthropic (Claude)** — no public OAuth for the API. Access is by API key only.
- **OpenAI** — no public OAuth for the API. Access is by API key only.
- **Google Gemini** — this one does have a real sign-in path, through Google Cloud.

So: Gemini gets a genuine "Sign in with Google" flow. Claude and OpenAI get a proper, verified key connection (the key is checked against the live API before it is accepted, and it is never shown back to the browser). The setup guide explains exactly where to get each one, step by step, and says plainly why two of them are keys rather than sign-in.

## Part 1 — Gemini sign-in (real OAuth)

- Add `gemini_oauth` to the backend OAuth config: Google consent screen, `cloud-platform` scope, same callback shape as Drive/Calendar (`/integrations/oauth/gemini_oauth/callback`), same automatic token renewal.
- Connect dialog asks for the Google Cloud project ID (Vertex AI needs it) before opening the sign-in window.
- Gemini answers are then produced with the signed-in account's access token through Vertex AI; the existing key-based Gemini connector stays as the simpler alternative.
- The connector card shows which Google account is signed in.

## Part 2 — Claude and OpenAI, properly connected

- Keep the key connection but make it real end to end: the key is verified with a live call at connect time, stored server-side only, masked on the card, and used by the Ask composer.
- Models from every connected provider already appear in the Ask picker; confirm Claude, OpenAI, Gemini (key and signed-in) all list and run.

## Part 3 — Setup guide

Append to `docs/CONNECTOR_OAUTH_SETUP.md`:

- Google Cloud: create the project, enable Vertex AI, create the OAuth client, add the callback URL, publish the consent screen, copy client ID/secret.
- Anthropic Console: workspace, billing, create key, restrict it, where to paste it in HakiScribe with the note that Anthropic publishes no OAuth for API access.
- OpenAI Platform: project, billing, create key, restrict it, where to paste it with the same note.
- A short table of every environment variable the backend reads for these.

## Part 4 — Login page

- New `/login` page in the HakiChain style: email + password, and a **Use demo credentials** button that fills and submits the judging account in one tap. The demo button is clearly marked temporary (hackathon judging) so it can be removed in one edit.
- `/new`, `/tracker`, `/settings`, `/research` and `/sessions/{id}` require a signed-in user; visiting them signed-out sends you to `/login` and back afterwards.
- The public landing page at `/` stays public, with a "Sign in" action.
- Sign-in is checked by the backend (`POST /auth/login`) against accounts configured on the server plus the demo account, and the session is kept in the browser until sign-out. Header gains a sign-out control.

### Scope note

This makes the private side invisible without signing in. It does not yet split the case library into separate per-lawyer vaults every signed-in user sees the same workspace. Say the word and that's the next piece.

## Technical notes

- Backend: `app/services/oauth.py` (new `gemini_oauth` entry + Vertex completion path in `integrations.py`), `app/routers/integrations.py` (project-ID capture), new `app/routers/auth.py` + `app/services/auth.py` (accounts from `HAKISCRIBE_USERS`, demo account from `DEMO_EMAIL`/`DEMO_PASSWORD`, signed token).
- Frontend: `src/routes/login.tsx`, `src/lib/auth.ts` (token store + `useAuth`), route guards via `beforeLoad` on the private routes, sign-out in `shell.tsx`, connector card changes in `connectors.tsx`.
- No change to the transcript pipeline, action tray, or generation.