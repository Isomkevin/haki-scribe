# HakiScribe Trigger.dev tasks (legacy path)

The **canonical** Trigger.dev worker lives at the **repo root**:

- Config: `trigger.config.ts`
- Tasks: `src/trigger/` (`detect-actions`, `generate-actions`, `research-actions`)
- Scripts: `npm run trigger:dev` / `npm run trigger:deploy`

This `hakiscribe-backend/trigger/` folder is kept as a reference for the
Python relay pattern. Prefer editing `src/trigger/` so `trigger.dev` registers
one worker.

Tasks are thin relays into the Python backend — see the header comment in each
file. This project holds no business logic on purpose: the LLM prompts,
Ambiguous AI calls, and matter-continuity logic all live in
`action_detector.py` / `action_executor.py` on the backend side, so there's
exactly one place to change them.

## Setup

```
# From the repo root
npm run trigger:dev
```

`hakiscribe-backend/.env.local` is only read by the FastAPI process and
by `npx trigger.dev@latest deploy` (via `syncEnvVars`). The running
tasks on Trigger.dev's cloud do **not** read that file.

Set these in the Trigger.dev dashboard Environment Variables, or redeploy
so `syncEnvVars` copies them from the root / backend `.env.local`:

- `BACKEND_INTERNAL_URL` = `https://hakiscribe-backend.onrender.com`
- `BACKEND_INTERNAL_SECRET` = the same value as Render's
  `BACKEND_INTERNAL_SECRET`

Then on the Render service, set `TRIGGER_SECRET_KEY` to the **prod**
secret from Trigger.dev → Project → API Keys (`tr_prod_...`). That is
what turns on the Trigger.dev path in `/sessions/{id}/detect` and
`/generate`. Without it, both endpoints fall back to the same logic
in-process.

Root frontend `.env.local` also needs `TRIGGER_SECRET_KEY` /
`TRIGGER_PROJECT_REF` for local `npm run trigger:dev` (see repo-root
`.env.example`).

## Deploy

```
# From the repo root
npm run trigger:deploy
```

## Why bother, if it's just a relay?

Retries, timeouts, and observability on the parts of the pipeline most
likely to transiently fail (LLM calls, Ambiguous AI calls, Exa research) —
for free, without hand-rolling retry logic in Python. The Trigger.dev
dashboard also gives you a live view of every detection / generation /
research run during the demo, which is a good thing to have open on a
second screen.
