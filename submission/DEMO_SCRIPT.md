# Demo video script — one unbroken take (~3–4 minutes)

Record screen + mic. Use a consented code-switched legal snippet (under 90 seconds).

## 0. Fast path (no mic) — multilingual seeds

1. Private workspace → **New session** screen  
2. Click **Open multilingual court & client demos**  
3. Library gains six EN–SW / Sheng sessions mixed among existing matters (titles look like normal desk work):
   - Court proceeding — Milimani Commercial Court, Wanjiru Holdings lease arrears
   - Voice memo — Wanjiru Holdings, Kilimani remedial works follow-up
   - Client briefing — Otieno, ELRC directions after mention
   - Client call — Coastal Sacco, Nyali statutory notice plan
   - Follow-up intake — Githunguri succession, revocation advice
   - Site briefing — Karanja & Sons, Westlands distress after lock-out  
4. Walk Action Tray on any of them; optional: connect Intron and record live for the video

---

## 1. Connect Intron (15s)

1. Open HakiScribe → **Settings → Connectors**
2. Find **Intron Sahara (Voice AI)**
3. Paste API key from voice.intron.io → Developers → **Connect**
4. Confirm connected badge

## 2. New multilingual session (20s)

1. **New session** → source **Microphone**
2. Language: **English + Kiswahili** or **Multilingual / African code-switch (Sahara)**
3. Note the inline hint that Sahara refines on Stop
4. **Start recording**

## 3. Record code-switched legal speech (45–60s)

Speak naturally (example):

> "Mheshimiwa, Civil Suit Milimani CS 204 — Wanjiru Holdings versus Kamau Enterprises. The defendant owes KES 450000. Hatutaki kucheleweshwa tena; we request a hearing within thirty days."

- Tap **Flag** once on a key admission or date
- **Stop** — wait for **"Refining with Sahara…"** then success toast

## 4. Speakers and privilege (30s)

1. **Speaker screen** — relabel Speaker 1 (e.g. "Adv. Wairimu")
2. **Redact screen** — lock one line as privileged/off-record (show it excluded later)

## 5. Action Tray → draft (45s)

1. **Analyze** → Action Tray appears with draft_document, calendar, matter, etc.
2. Select **draft document** → **Generate**
3. Open result — show letter grounded in transcript
4. Optional: **View source** jump to segment

## 6. Benchmark mention (15s)

Briefly show `submission/BENCHMARK_RESULTS.md` or run:

```bash
cd hakiscribe-backend && python -m benchmarking.run_benchmark
```

## Closing line

"HakiScribe turns African code-switched legal speech into structured work — with Sahara for the transcript and an Action Tray for what leaves the desk."
