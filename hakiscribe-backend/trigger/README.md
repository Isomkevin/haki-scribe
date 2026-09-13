# HakiScribe Trigger.dev tasks

Two tasks, both thin relays into the Python backend — see the header
comment in each file. This project holds no business logic on purpose:
the LLM prompts, Ambiguous AI calls, and matter-continuity logic all
live in `action_detector.py`/`action_executor.py` on the backend side,
so there's exactly one place to change them.

## Setup

```
cd trigger
npm install
npx trigger.dev@latest login
npx trigger.dev@latest init     # links this to your Trigger.dev project
```

Replace `proj_hakiscribe_replace_me` in `trigger.config.ts` with the
project ref from the dashboard (`proj_...`).

Set these in the Trigger.dev dashboard Environment Variables (the tasks
run on Trigger.dev's cloud, not Render):

- `BACKEND_INTERNAL_URL` = `https://hakiscribe-backend.onrender.com`
- `BACKEND_INTERNAL_SECRET` = the same value as Render's
  `BACKEND_INTERNAL_SECRET`

Then on the Render service, set `TRIGGER_SECRET_KEY` to the **prod**
secret from Trigger.dev → Project → API Keys (`tr_prod_...`). That is
what turns on the Trigger.dev path in `/sessions/{id}/detect` and
`/generate`. Without it, both endpoints fall back to the same logic
in-process.

## Deploy

```
npx trigger.dev@latest deploy
```

## Why bother, if it's just a relay?

Retries, timeouts, and observability on the parts of the pipeline most
likely to transiently fail (LLM calls, Ambiguous AI calls) — for free,
without hand-rolling retry logic in Python. The Trigger.dev dashboard
also gives you a live view of every detection/generation run during the
demo, which is a good thing to have open on a second screen.
