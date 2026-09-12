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
npx trigger.dev@latest init     # links this to your Trigger.dev project
```

Set these in the Trigger.dev dashboard's environment variables (not a
local `.env` — the tasks run on Trigger.dev's infrastructure, not yours):

- `BACKEND_INTERNAL_URL` — a **publicly reachable** URL for the FastAPI
  backend. `localhost` will not work here since Trigger.dev's cloud is
  calling it. Use an ngrok tunnel for local dev.
- `BACKEND_INTERNAL_SECRET` — must match `BACKEND_INTERNAL_SECRET` in
  the FastAPI backend's `.env`.

Then on the FastAPI backend side, set `TRIGGER_SECRET_KEY` (from the
Trigger.dev dashboard's API keys page) — that's what turns on the
Trigger.dev path in `/sessions/{id}/detect` and `/generate`. Without it,
both endpoints fall back to running the exact same logic in-process,
so nothing breaks if this isn't wired up yet.

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
