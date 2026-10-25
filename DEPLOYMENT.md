# HakiScribe — Dual Deployment Guide (Lovable + Vercel)

HakiScribe is one codebase deployed to two frontends:

- **Lovable** (`https://hakiscribe.lovable.app`) — the existing production deployment.
- **Vercel** — enabled and verified, not yet deployed (see [Status](#status)).

## Architecture (what runs where)

| Piece | Where it runs | Notes |
|---|---|---|
| Frontend + SSR + server functions (TanStack Start on Vite/nitro) | Lovable (Cloudflare) **or** Vercel (Node 22 functions) | Same source; nitro picks the target automatically |
| FastAPI backend (`hakiscribe-backend/`) | Render — `https://hakiscribe-backend.onrender.com` | **Shared by both frontends.** Never duplicated for Vercel |
| Transcription, detection, generation, exports | Render backend (+ Trigger.dev tasks in `src/trigger/`) | Trigger.dev is its own platform, unaffected by frontend hosting |
| Session / sign-in | Browser-held token from the backend | No Supabase; no per-frontend auth config needed for demo-token sign-in |
| Connector OAuth callbacks | Render (`/integrations/oauth/{provider}/callback`) | No per-frontend redirect URLs |

The frontend talks to the backend using `VITE_API_BASE_URL` (committed in `.env`; the constant `PRODUCTION_API_URL` in `src/lib/hakiscribe.ts` is the final fallback). No other frontend hosting assumption exists.

## Vercel deployment

### 1. Import the project

Vercel dashboard → **Add New → Project** → import the connected Git repository. Root directory: repository root (the FastAPI backend lives in a subfolder but is not built by Vercel).

### 2. Build settings

The build is zero-config: when it runs on Vercel, nitro detects the Vercel target and emits a complete [Build Output API](https://vercel.com/docs/build-output-api) bundle in `.vercel/output/` (verified locally — function entry, routing, and static assets are all generated).

- **Framework preset:** leave Vercel's auto-detection (Vite), or set **Other**.
- **Build command:** `npm run build` (or `bun run build`).
- **Output directory:** leave empty. If Vercel insists on one, set it to `.vercel/output/static`.
- Do **not** create a `vercel.json` — nitro generates the routing config, and a hand-written one can conflict.

### 3. Package manager

Both `bun.lock` and `package-lock.json` are committed and kept in sync. Vercel auto-detects one of them; if an install step misbehaves, set **Install Command** to `bun install` explicitly.

### 4. Node version

Build step requires Node ≥ 20.19 (declared in `package.json` → `engines`). The generated serverless functions pin `nodejs22.x`.

### 5. Environment variables (Project Settings → Environment Variables)

| Variable | Type | Required | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Build-time, public | Recommended | Backend URL. The committed `.env` already supplies `https://hakiscribe-backend.onrender.com`; a Vercel variable overrides it if you want a different backend. |
| `VITE_PRODUCTION_AUTH` | Build-time, public | Optional | `true` only if the backend runs with `HAKISCRIBE_PRODUCTION_AUTH=true` (cookie sign-in surface). Same value as on Lovable. |
| `LOVABLE_API_KEY` | Server-side secret | Optional | Powers the Research page's AI generation through the Lovable AI Gateway. Without it, Research shows a clear "not configured" message; everything else works. |
| `EXA_API_KEY` | Server-side secret | Optional | Citation search that backs Research. |

**Never put on Vercel:** `BACKEND_INTERNAL_SECRET`, `SUPABASE_SERVICE_KEY`, or any backend/Trigger.dev secret — those belong to Render and the Trigger.dev dashboard and are already isolated server-side. Do not prefix server-side secrets with `VITE_`.

### 6. Deploy

- **Production:** push to the connected branch (or click *Deploy* in the dashboard).
- **Preview:** every pull request gets its own preview URL with the same env vars (mark secrets as available to Preview).

### 7. Post-deployment verification

1. `/` renders the landing page; no case data leaks on the public page.
2. `/login` sign-in works with workspace credentials (browser session — nothing to configure).
3. `/new` → start a session; `/tracker`, `/contacts`, `/settings` load and refresh.
4. Deep-link refresh on a nested route (e.g. `/tracker`, `/contacts/<id>`) does not 404 — the `__server` function handles all routes.
5. `/research` runs if `LOVABLE_API_KEY` is set; otherwise shows the "not configured" message (expected).
6. Connectors page statuses respond (live calls to the Render backend).
7. Microphone recording works (HTTPS is automatic on Vercel; grant the permission).
8. PWA: `sw.js` and `manifest.webmanifest` served from `/`; install prompt works.

## Lovable deployment (preserved)

Nothing in this change touches the Lovable build path: Lovable's sandbox pins the `cloudflare-module` nitro preset, and the Vercel behaviour only activates when nitro detects a Vercel target. Keep publishing from the Lovable editor as before. Do not rename `src/server.ts` or change `vite.config.ts`'s `tanstackStart.server.entry` without re-verifying **both** platforms.

## Authentication & backend configuration

- **Demo-token sign-in** (current): the session lives in the browser and is validated by the Render backend. Works identically on both domains; nothing to configure.
- **Production auth** (`HAKISCRIBE_PRODUCTION_AUTH=true` on Render): add each frontend origin to `HAKISCRIBE_ALLOWED_ORIGINS` on Render, e.g. `https://hakiscribe.lovable.app,https://<your-app>.vercel.app,https://<custom-domain>`. Avoid a blanket `*`. Auth cookies are per-domain, so Lovable and Vercel sessions are independent — that is expected.
- **Connector OAuth:** callbacks stay at `https://hakiscribe-backend.onrender.com/integrations/oauth/{provider}/callback`. No per-frontend redirect URLs are needed.

## Behaviour on Vercel vs Lovable

- **Same:** all routing (SSR serves deep links and refreshes), assets, PWA/service worker, the SSR 500 error page wrapper (`src/server.ts` — verified present in the Vercel function entry), CSRF-protected server functions.
- **`public/_headers`** is a Cloudflare/Lovable convention; Vercel ignores it. The `/assets/*` immutable caching is reproduced in the generated Vercel routing config, and browsers bypass the HTTP cache when checking `sw.js` for updates, so no replacement is needed.
- **Research page** needs `LOVABLE_API_KEY` on whichever platform serves it.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build failure on Vercel | Reproduce locally outside the Lovable sandbox: `NITRO_PRESET=vercel npm run build` (unset `LOVABLE_SANDBOX` / `DEV_SERVER__PROJECT_PATH` if present). Check Node ≥ 20.19. |
| Nested route 404 on refresh | Build didn't emit `.vercel/output` (nitro vercel preset) — confirm the build log shows `Generated .vercel/output/nitro.json`. |
| "HakiScribe cannot reach its service…" | `VITE_API_BASE_URL` missing at build time — set it in Vercel env vars. |
| API calls fail / CORS | Render may be asleep (free tier cold start) or the origin isn't allowed — check `HAKISCRIBE_ALLOWED_ORIGINS` on Render. |
| Research says "not configured" | Set `LOVABLE_API_KEY` (and optionally `EXA_API_KEY`) in Vercel env vars. |
| Microphone blocked | Grant the site permission; both platforms serve HTTPS. |
| Assets 404 | Output directory was overridden to `dist` — leave it empty or use `.vercel/output/static`. |

## Rollback

- **Vercel:** Deployments → pick the last good deployment → **Promote to Production** (instant; never touches Lovable).
- **Lovable:** publish from the Lovable editor as usual; Vercel work cannot break an already-published Lovable site.

## Status

1. Code changes completed — **yes**
2. Build successful — **yes** (Lovable/sandbox build and a `NITRO_PRESET=vercel` build both verified)
3. Ready for Vercel deployment — **yes** (follow the steps above)
4. Vercel preview deployed — **no** (needs your Vercel account/repo connection)
5. Vercel production deployed — **no**
6. Production functionality verified — **not yet** (steps 1–8 above should be re-run on the live Vercel URL; recording, transcription and backend-dependent behaviour were not verifiable without a deployment)
