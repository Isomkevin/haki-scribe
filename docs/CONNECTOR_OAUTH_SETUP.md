# Connector OAuth setup guide

This guide walks you through creating the OAuth apps at **Google**, **Dropbox**, and **Microsoft**, and adding their credentials to your Render deployment so that HakiScribe's **Connectors** page can offer real "Sign in with Google / Dropbox / Microsoft" connections and push documents and calendar events to real storage.

Each section is self-contained — do them in any order. When you finish a provider, its card on the Connectors page changes from *"not configured on this server"* to a working **Sign in** button.

---

## What you are setting up

HakiScribe lets a lawyer link their own cloud storage and calendar from the Connectors page. The browser never sees a token: it opens a sign-in popup, the provider redirects back to the backend, and the backend exchanges the code for tokens and stores them server-side. Access tokens are refreshed automatically before each export.

Four providers use this flow:

| Provider ID         | Card label          | What it enables                                            |
| ------------------- | ------------------- | --------------------------------------------------------- |
| `google_drive`      | Google Drive        | Export drafted documents to the signed-in user's Drive    |
| `google_calendar`   | Google Calendar     | "Add to Google Calendar" on generated court/client dates   |
| `dropbox`           | Dropbox             | Export drafted documents to the signed-in user's Dropbox   |
| `onedrive`          | Microsoft OneDrive  | Export drafted documents to the signed-in user's OneDrive |

Google Drive and Google Calendar share **one** Google OAuth client — you only create it once.

The exact callback URL the provider must be told is:

```
https://hakiscribe-backend.onrender.com/integrations/oauth/{provider_id}/callback
```

Replace `{provider_id}` with `google_drive`, `google_calendar`, `dropbox`, or `onedrive`. Each of these four URLs must be added as an **Authorized redirect URI** in the matching app.

---

## Before you start

You will need:

- Access to the **Render** dashboard for the `hakiscribe-backend` service (to set environment variables and deploy).
- A Google account, a Dropbox account, and a Microsoft (Entra ID / Azure) account that can create app registrations.

Have the backend `.env.example` open for reference (`hakiscribe-backend/.env.example`). The environment variable names below match that file exactly.

---

## 1. Google (Google Drive + Google Calendar)

One Google Cloud project + one OAuth client covers **both** Google Drive and Google Calendar.

### 1.1 Create the Google Cloud project

1. Go to **https://console.cloud.google.com/**.
2. At the top, open the project picker → **NEW PROJECT**.
3. Name it (e.g. `HakiScribe`) → **CREATE**.
4. Wait for the project to be selected (the top bar shows its name).

### 1.2 Enable the APIs

1. Left menu → **APIs & Services → Library**.
2. Search **Google Drive API** → open it → **ENABLE**.
3. Back to the Library, search **Google Calendar API** → open it → **ENABLE**.

Both must show "API enabled" before consent will work.

### 1.3 Configure the OAuth consent screen

1. Left menu → **APIs & Services → OAuth consent screen**.
2. User type: choose **External** (unless you have a Google Workspace and want internal) → **CREATE**.
3. App information:
   - App name: `HakiScribe`
   - User support email: your email
   - App logo (optional)
4. App domain: fill in what you have (e.g. `hakiscribe.lovable.app` for the app, `hakiscribe-backend.onrender.com` is not a homepage — leave homepage blank if unsure).
5. Authorized domains: add `lovable.app` and `onrender.com` if you reference them.
6. Developer contact information: your email → **SAVE AND CONTINUE**.
7. **Scopes** step → **Add or Remove Scopes**:
   - Add these exact scopes:
     - `https://www.googleapis.com/auth/drive.file` — upload files the app created
     - `https://www.googleapis.com/auth/calendar.events` — create calendar events
     - `openid` — basic profile
     - `email` — read the signed-in user's email for the card label
   - Click **UPDATE** → **SAVE AND CONTINUE**.
8. **Test users** step → **Add Users** → add the Google accounts of yourself and any lawyer who will test. (While the app is in "Testing" status, only listed test users can consent.) → **SAVE AND CONTINUE**.
9. Review the summary → **BACK TO DASHBOARD**.

> To allow anyone to connect later, submit the app for **Verification** (Publishing → Push to production). For a small firm, leaving it in Testing and adding users is enough.

### 1.4 Create the OAuth client

1. Left menu → **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Name: `HakiScribe web client`.
4. **Authorized JavaScript origins**: add `https://hakiscribe-backend.onrender.com`.
5. **Authorized redirect URIs** — add these two exactly (no trailing slash beyond the path):
   ```
   https://hakiscribe-backend.onrender.com/integrations/oauth/google_drive/callback
   https://hakiscribe-backend.onrender.com/integrations/oauth/google_calendar/callback
   ```
6. **CREATE**.
7. A dialog shows your **Client ID** and **Client secret**. Copy both — you will paste them into Render.

### 1.5 Add the credentials to Render

In the `hakiscribe-backend` service on Render → **Environment**, set:

| Variable name                 | Value                  |
| ----------------------------- | ---------------------- |
| `GOOGLE_OAUTH_CLIENT_ID`      | the Client ID          |
| `GOOGLE_OAUTH_CLIENT_SECRET`  | the Client secret      |

Optional (calendar behaviour):

| Variable name             | Value                                                         |
| ------------------------- | ------------------------------------------------------------- |
| `GOOGLE_CALENDAR_ID`      | `primary` (default — uses the signed-in user's main calendar) |
| `GOOGLE_CALENDAR_TIMEZONE`| `Africa/Nairobi` (default) — set to your local IANA timezone   |

Save, then trigger a deploy (or let the next deploy pick them up).

---

## 2. Dropbox

### 2.1 Create the Dropbox app

1. Go to **https://www.dropbox.com/developers/apps** → **Create app**.
2. Choose an API:
   - **1. Choose an API** → **Scoped access**.
   - **2. Choose the type of access** → **App folder** (the app only sees its own folder — safer) **or Full Dropbox** (sees everything — avoid unless required).
3. **3. Name your app** → e.g. `HakiScribe` → **Create app**.

### 2.2 Set the redirect URI

1. On the app's **Settings** tab, find **OAuth 2 → Redirect URIs**.
2. Add exactly:
   ```
   https://hakiscribe-backend.onrender.com/integrations/oauth/dropbox/callback
   ```
3. Find **OAuth 2 → Access token expiration** → set to **No expiration** is not available; leave **Short-lived (about 4 hours)** — the backend refreshes automatically using the refresh token.
4. Under **OAuth 2**, make sure **Allow implicit grant** is OFF and **Use PKCE** is optional (the backend uses the confidential client flow with a secret, so PKCE is not required).

### 2.3 Set the scopes (Permissions tab)

1. Open the **Permissions** tab.
2. Select these exact scopes:
   - `files.content.write` — upload drafted documents
   - `files.content.read` — read files back if needed
   - `account_info.read` — read the account email for the card label
3. **Save** at the bottom, then go back to **Settings** and click **Submit** / **Apply** if the scope changes require it.

### 2.4 Get the app key and secret

On the **Settings** tab:

- **App key** → this is the client id.
- **App secret** → click **Show** → this is the client secret.

### 2.5 Add the credentials to Render

In the `hakiscribe-backend` service on Render → **Environment**, set:

| Variable name          | Value        |
| ---------------------- | ------------ |
| `DROPBOX_APP_KEY`      | the App key  |
| `DROPBOX_APP_SECRET`   | the App secret |

Save and deploy.

> The backend also accepts `DROPBOX_CLIENT_ID` / `DROPBOX_CLIENT_SECRET` as alternate names, but prefer `DROPBOX_APP_KEY` / `DROPBOX_APP_SECRET`.

---

## 3. Microsoft (OneDrive)

### 3.1 Register the app in Microsoft Entra ID

1. Go to **https://entra.microsoft.com/** → **Applications → App registrations → New registration**.
   (Equivalent Azure portal path: **https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade** → **New registration**.)
2. Name: `HakiScribe`.
3. **Supported account types** — choose based on who will connect:
   - **Accounts in any organizational directory (Any Entra ID tenant - multitenant)** + **Personal Microsoft accounts (Outlook.com)** is the broadest, and lets personal Microsoft accounts connect too.
   - If everyone at your firm is on one Entra tenant, pick **Accounts in this organizational directory only (Single tenant)** — but then each connecting user must be in that tenant.
4. **Redirect URI** → platform **Web** → paste exactly:
   ```
   https://hakiscribe-backend.onrender.com/integrations/oauth/onedrive/callback
   ```
5. **Register**.

> If you chose **Single tenant**, note the **Directory (tenant) ID** shown on the app's Overview page — you must set `MICROSOFT_TENANT_ID` to that GUID in Render. The default `common` only works for multitenant registrations.

### 3.2 Add a client secret

1. Left menu → **Certificates & secrets → Client secrets → New client secret**.
2. Description: `HakiScribe backend`, expiry: choose as long as your policy allows → **Add**.
3. Copy the **Value** (not the Secret ID) immediately — it is hidden once you leave the page. This is your client secret.

### 3.3 Grant API permissions (delegated)

1. Left menu → **API permissions → Add a permission → Microsoft Graph → Delegated permissions**.
2. Add these exact permissions:
   - `offline_access` — required so the backend can refresh the access token
   - `Files.ReadWrite` — upload drafted documents to the signed-in user's OneDrive
   - `User.Read` — read the account label for the card
3. **Add permissions**.
4. You do **not** need admin consent for these delegated permissions for personal Microsoft accounts. For a single-tenant org, an admin may need to click **Grant admin consent for [tenant]** so users do not get a consent prompt.

### 3.4 Add the credentials to Render

In the `hakiscribe-backend` service on Render → **Environment**, set:

| Variable name                | Value                                  |
| ---------------------------- | -------------------------------------- |
| `MICROSOFT_CLIENT_ID`        | the Application (client) ID            |
| `MICROSOFT_CLIENT_SECRET`    | the client secret **Value** from 3.2   |
| `MICROSOFT_TENANT_ID`        | the Directory (tenant) ID **only for single-tenant** — omit (or leave `common`) for multitenant |

Save and deploy.

> The backend also accepts `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` as alternate names, but prefer the `MICROSOFT_*` names.

---

## 4. Deploy and verify

After setting the variables, deploy the backend on Render (Render → Manual Deploy → Deploy latest commit, or clear build cache if the last deploy failed).

### 4.1 Check the Connectors page

1. Open the published HakiScribe app.
2. Go to **Connectors** (next to Case tracker on the home screen).
3. Each card should now show a **Sign in with Google / Dropbox / Microsoft** button instead of the "not configured on this server" hint.

### 4.2 Sign in and test

For each provider:

1. Click **Sign in**.
2. A popup opens; complete consent with the test account you added.
3. The popup closes and the card shows **"Signed in as you@…."**.
4. Test the outcome:
   - **Google Drive / Dropbox / OneDrive**: open a session with a drafted document → the result card's **Export** menu lists the connected provider → choose it → confirm the file appears in your cloud storage.
   - **Google Calendar**: open a session with a generated court/client date → click **Add to Google Calendar** → confirm the event appears in your calendar.

### 4.3 Token refresh

Access tokens are short-lived (~1 hour for Google, ~4 hours for Dropbox, ~1 hour for Microsoft). The backend stores the **refresh token** and automatically refreshes before each provider call, so connections keep working without you re-signing-in. If a refresh ever fails (e.g. the user revoked access), the card returns to the **Sign in** state.

---

## 5. Troubleshooting

| Symptom                                                              | Likely cause / fix                                                                                                                                                |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Card still shows "not configured on this server"                     | The env var was not set on Render, or the backend was not redeployed. Confirm the variable name and deploy.                                                        |
| Sign-in popup shows "redirect_uri_mismatch"                         | The redirect URI in the provider console does not exactly match `https://hakiscribe-backend.onrender.com/integrations/oauth/{provider}/callback` (check trailing slash, http vs https). |
| Google sign-in: "access blocked: app not verified"                  | App is in Testing status and the connecting user was not added as a test user. Add them under OAuth consent screen → Test users, or publish the app.             |
| Dropbox sign-in: "invalid_grant" / missing refresh token            | The app was created without `token_access_type=offline`. The backend requests offline access at sign-in, so confirm the Dropbox app allows it; reconnect.        |
| Microsoft sign-in: AADSTS50194                                      | The registration is single-tenant but `MICROSOFT_TENANT_ID` is `common`. Set it to the tenant GUID, or change the registration to multitenant.                    |
| Microsoft sign-in: personal account fails                           | The registration's "Supported account types" does not include personal Microsoft accounts. Recreate or edit the registration to include them.                   |
| Token refreshed but export still 401                                 | The API/scopes were not enabled (Google Drive/Calendar API) or the permission was not added (Microsoft Graph `Files.ReadWrite`). Enable/add and re-consent.      |

---

## 6. Environment variable reference

All names match `hakiscribe-backend/.env.example`.

| Variable                     | Provider(s)                                |
| ---------------------------- | ------------------------------------------ |
| `GOOGLE_OAUTH_CLIENT_ID`     | Google Drive, Google Calendar (shared)    |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google Drive, Google Calendar (shared)    |
| `GOOGLE_CALENDAR_ID`         | Google Calendar (optional, default `primary`) |
| `GOOGLE_CALENDAR_TIMEZONE`   | Google Calendar (optional, default `Africa/Nairobi`) |
| `DROPBOX_APP_KEY`            | Dropbox                                    |
| `DROPBOX_APP_SECRET`         | Dropbox                                    |
| `MICROSOFT_CLIENT_ID`        | Microsoft OneDrive                         |
| `MICROSOFT_CLIENT_SECRET`    | Microsoft OneDrive                         |
| `MICROSOFT_TENANT_ID`        | Microsoft OneDrive (optional; set for single-tenant) |
| `OAUTH_REDIRECT_BASE_URL`   | Optional override; defaults to `BACKEND_INTERNAL_URL` (`https://hakiscribe-backend.onrender.com`). Use `http://127.0.0.1:8000` for local testing. |

Set these in **Render → hakiscribe-backend → Environment**, then deploy. Do **not** put them in the committed `.env` — secrets must live in Render's environment, not in the repo.

---

## AI model connectors

### Google Gemini — real "Sign in with Google" (Vertex AI)

Gemini is the one AI provider with a genuine OAuth sign-in, because Vertex
AI accepts Google account tokens.

1. Reuse the same OAuth client you created for Drive/Calendar
   (`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`).
2. Add this callback to the client's authorised redirect URIs:
   `{BACKEND_INTERNAL_URL}/integrations/oauth/gemini_oauth/callback`
3. In the same Google Cloud project, enable **Vertex AI API**.
4. Give the signed-in account the **Vertex AI User** role on that project.
5. On the Connectors page, choose *Google Gemini (sign in)*, enter the
   Google Cloud **project ID** (and optionally a region — default
   `us-central1`), then complete the Google consent screen.

The scope requested is `cloud-platform`; the access token is refreshed
automatically and never leaves the server. Connected Gemini models appear
in the "Ask an AI model" picker as *Gemini … (signed in with Google)*.

### Anthropic (Claude) and OpenAI — verified key connections

Neither Anthropic nor OpenAI offers a public OAuth flow for API access;
there is no "Sign in with Claude" to build against. Both are therefore
connected with an API key that HakiScribe verifies live at connect time,
stores server-side only, and shows masked on the card.

**Anthropic**
1. Sign in at https://console.anthropic.com
2. Settings → API keys → **Create key** (scoped to a workspace if you want
   a separate budget for HakiScribe).
3. Copy the `sk-ant-…` key into the Connectors page → *Anthropic (Claude)*.

**OpenAI**
1. Sign in at https://platform.openai.com
2. **API keys** → *Create new secret key*; give it a project so usage is
   visible separately.
3. Copy the `sk-…` key into the Connectors page → *OpenAI*.

A key that fails verification is never saved, so a typo is reported on the
card instead of silently failing later during a session.

---

## Private workspace sign-in

Recording, transcripts, the case tracker, research and settings sit behind
a sign-in. Accounts are configured on the server:

```
HAKISCRIBE_USERS="advocate@firm.co.ke:strong-password|Jane Advocate, clerk@firm.co.ke:another"
AUTH_SECRET=<any long random string — keeps sign-ins valid across restarts>
```

A **temporary demo account** is enabled by default so a judge can open the
private side in one tap (`DEMO_EMAIL` / `DEMO_PASSWORD`, defaults
`demo@hakiscribe.app` / `hakiscribe-demo`). Set `DEMO_LOGIN_ENABLED=false`
to remove the demo button and the account entirely before real client work.

Scope note: everyone signed in shares the same workspace today. Per-lawyer
vaults are the next step.
