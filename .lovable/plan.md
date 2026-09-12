# Turn the transcript into a full action workbench

Today the tray can draft documents, set calendar events, open matters, log CRM entries, private notes and time entries. This adds research and free-form AI work to the same tray, all running as durable background jobs.

## New things a session can produce

1. **Legal research** — takes a legal question actually raised in the conversation (a statute, a limitation period, a procedural rule), searches Kenyan legal sources on the web, and returns a short memo: the question, the answer, and a list of sources with links. Sources are always shown; nothing is presented as fact without one.
2. **Web search / background check** — looks up a company, person or matter named in the conversation and returns a labelled background brief with links. Never folded into a legal draft.
3. **Ask an AI model** — a free-form instruction run against the verified transcript ("summarise for the partner", "list every commitment my client made", "draft talking points for the mention"). The user can choose which model answers it — Claude, GPT, Gemini or any other model available through the connected gateway.
4. **Word document in Ambiguous** — every generated draft can be pushed into Ambiguous as a real document, and the result card links straight to it, with a notification posted for review.

Each of these appears as its own card in the tray, individually selectable, with a source line back to the transcript, exactly like the existing cards.

## How they run

All of it goes through the same durable pipeline that detection and generation already use: the work is handed to Trigger.dev, retried on failure, and the app polls for the result. If Trigger.dev is not configured the same work runs directly, so nothing breaks.

Research and AI calls can take a while, so the generate step gets a longer patience window and per-card progress rather than one global spinner.

## Where it is built

**Backend (`hakiscribe-backend`)**
- `app/models/schemas.py` — add `legal_research`, `web_search`, `llm_task` action types and result models (`ResearchResult` with `question`, `answer`, `sources[]`; `LlmTaskResult` with `model`, `instruction`, `output`).
- `app/integrations/exa_client.py` — add `search_legal(query)` (Kenyan law domains, text contents) alongside the existing company search.
- `app/integrations/llm_client.py` (new) — one OpenRouter-backed entry point taking an explicit model id, so Claude/GPT/Gemini are all reachable; lists the available models for the picker.
- `app/services/action_detector.py` — heuristics that raise a research card when a statute/section/limitation question is voiced, and a background-check card when an unfamiliar organisation is named.
- `app/services/action_executor.py` — executors for the three new types; research = Exa retrieval then model synthesis constrained to retrieved sources; llm_task = instruction + non-redacted transcript.
- `app/routers/actions.py` — new `POST /sessions/{id}/ask` for an ad-hoc instruction card, and `GET /models` for the picker.
- `trigger/researchActions.ts` (new) — relay for the longer-running research/LLM work; `trigger.config.ts` gains a longer max duration.

**Frontend**
- `src/lib/hakiscribe.ts` — new types, `ask()` and `listModels()`.
- `src/components/hakiscribe/app.tsx` — new card icons and result renderers (memo with clickable sources, background brief, model answer), plus an "Ask anything about this session" composer under the tray with a model picker.

**Config** — `EXA_API_KEY`, `OPENROUTER_API_KEY`, `AMBIGUOUS_API_KEY`, `TRIGGER_SECRET_KEY`. Anything unset degrades gracefully with an honest message on the card instead of a fake result.

## Checks before finishing

Run a seeded session end to end against the local backend: detect, generate a research card, a background check, and a free-form ask on two different models, and confirm every card returns real content with real sources.
