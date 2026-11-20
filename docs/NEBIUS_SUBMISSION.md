# HakiScribe — Nebius × NVIDIA Global AI Hackathon

**Track:** Best Apps and Agents  
**Bonus:** Best Use of Tavily (functional runtime search in research actions)  
**Also eligible for:** Overall awards; Most Valuable Feedback (complete the feedback section)

**Live app:** https://hakiscribe.lovable.app/  
**API health:** https://hakiscribe-backend.onrender.com/health  
**Repo:** https://github.com/Isomkevin/haki-scribe  
**License:** MIT (see `LICENSE` at repo root)

---

## One-sentence positioning

HakiScribe is the legal work agent in the room: it listens to a client meeting, keeps privileged lines out of the model, and returns a selectable Action Tray of source-traced drafts, dates, and research — powered by NVIDIA Nemotron on Nebius Token Factory.

## Problem

After a client meeting or chambers discussion, Kenyan advocates still reconstruct the next demand letter, diary date, and matter update from memory. The detail that mattered is already gone — or worse, privileged speech is pasted into a generic chatbot.

## Target users

Advocates, judges, and clerks working in English, Kiswahili, and code-switched speech — starting with Kenya, designed as the listening instrument of [HakiChain](https://hakichain.com).

## Solution

1. **Listen** — phone/laptop mic or Omi wearable.  
2. **Flag** — mark moments without breaking eye contact.  
3. **Verify** — name speakers; lock privileged lines (visible, struck through, never sent to the model).  
4. **Propose** — Action Tray (not a chat): draft, calendar, matter, contact, time entry, note — each with a source quote.  
5. **Decide** — the professional selects, edits, and only then generates. Liability stays with the human.

## How Nebius and NVIDIA power the core journey

| Step | Model / service | Role |
| --- | --- | --- |
| Detect Action Tray | NVIDIA Nemotron **Super** via Nebius Token Factory | Propose source-grounded artifacts from the non-redacted transcript |
| Draft letter / memo | NVIDIA Nemotron **Ultra** via Token Factory | Generate editable legal prose for selected cards |
| Research action | **Tavily** (Kenyan legal domains) + Nemotron **Super** | Retrieve external authorities; synthesise with “not evidence” labelling |
| Utility (e.g. time entry) | Nemotron **Nano** when available | Cheap bounded prose |

Base URL: `https://api.tokenfactory.nebius.com/v1` (OpenAI-compatible). Model ids are discovered from `GET /models`, not hardcoded. When Nebius is connected, failures surface — there is **no silent fallback** to OpenRouter.

Speech-to-text remains on the existing ASR pipeline (Whisper / optional Intron Sahara). Token Factory is not used as ASR; eligibility is satisfied by runtime Token Factory chat completions with Nemotron.

## What makes it different

- Privilege is a product constraint, not a prompt suggestion.  
- The deliverable is the next document, not a transcript wall.  
- Tavily results are labelled **External authorities (not evidence)** — retrieval is not verification.  
- The lawyer chooses what leaves the desk.

## Significant updates during the Submission Period

HakiScribe predated August 26, 2026. During this hackathon we added / hardened: Nebius Token Factory + Nemotron tier routing, privilege interception tests, Tavily authority search for research actions, provider precedence so a connected Nebius key overrides a stale OpenRouter env default, live short demo (`/demo/live-nemotron`), diagnostics, and MIT license visibility. See README § “What was significantly updated”.

## Testing instructions for judges

1. Open https://hakiscribe.lovable.app/ → Sign in → **Use demo credentials**.  
2. `/new` → **Run live Nemotron demo** (primary button).  
3. Confirm speakers → confirm privilege (tax line struck) → continue to analysis.  
4. Wait for the Action Tray (Nemotron Super). Open **View source** on a card.  
5. Generate the demand letter (Ultra). Note the model footer.  
6. Run / open the research card — Tavily URLs + Super synthesis, labelled not evidence.  
7. Optional: Settings → Connectors → Test connection / Run diagnostics.

Saved sample (“Open saved sample”) is a prebuilt library artifact — **not** the eligibility path.

## Architecture (short)

```
Mic / Omi → FastAPI session → privilege filter
        → Trigger.dev or in-process
        → Detect (Nemotron Super @ Token Factory)
        → Generate (Ultra) | Research (Tavily + Super)
        → Action Tray → human edit → optional Ambiguous / WhatsApp handoff
```

## Realistic impact

Illustrative prototype only: no claimed user counts, win rates, or production GDPR certification in this submission. The demonstrated outcome is a privilege-safe, source-traced demand letter and research note from a short client intake that a lawyer can edit before service.

## Feedback

Paste honest observations from [`FEEDBACK.md`](./FEEDBACK.md) after a live smoke / UI run. Do not invent latency numbers.

---

## Devpost description (paste)

**Built with:** Nebius Token Factory, NVIDIA Nemotron (Super / Ultra / Nano), Tavily, FastAPI, TanStack Start, Trigger.dev

### Inspiration

Justice work in Kenya still often leaves the room as memory. Advocates need the next document — not another transcript chatbot that swallows privileged speech.

### What it does

HakiScribe captures a meeting (mic or Omi), requires speaker names, locks privileged lines out of the model, and proposes a selectable Action Tray of source-traced legal work. Detect runs on Nemotron Super via Nebius Token Factory; drafts on Ultra; research uses Tavily over Kenyan legal domains then Super synthesis, labelled external authorities — not evidence.

### How we built it

FastAPI backend + TanStack Start frontend. Token Factory OpenAI-compatible API with live model discovery. Privilege stripping and citation validation before any model call. Optional Trigger.dev for durable detect/generate.

### Challenges

Keeping Nebius as the real production path when deploy defaults still said OpenRouter; refusing silent provider fallback so the demo stays honest; distinguishing retrieval (Tavily) from verification.

### Accomplishments

A coherent room → privilege → tray → draft → research journey with MIT-licensed public source and a short live demo that forces Token Factory calls.

### What we learned

Eligibility means a runtime Token Factory call with an NVIDIA open model — the rest of the stack can stay elsewhere. Product constraints (privilege, source quotes) matter more to legal users than model theatre.

### What's next

Firm tenancy and production auth (see [PRODUCTION_READINESS.md](./PRODUCTION_READINESS.md)); measured latency from live smoke once keys are in place; deeper HakiChain matter sync.

### Built before this hackathon?

Yes. Significant updates during the Submission Period: Nebius/Nemotron compute layer, privilege interception, Tavily research path, provider precedence fix, live Nemotron demo endpoint, diagnostics, MIT license. Details in the README.
