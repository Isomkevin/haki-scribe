# HakiScribe — GOMYCODE Come Build with AI submission package

## Required links for the Google Form

| Form field | Link / file | Reviewer-access check |
| --- | --- | --- |
| Source code URL | https://github.com/Isomkevin/haki-scribe | Public repository; open in a private browser window. |
| Presentation URL | Upload `HakiScribe_GOMYCODE_Come_Build_With_AI.pptx` to Google Drive or Google Slides and paste an **Anyone with the link can view** URL here. | Required before submission. |
| 90-second demo video URL | https://youtu.be/FjsZqMBsCfs | Confirm it is public or unlisted and loads while signed out. |

The Google Form is the submission channel. GitHub, the deck, or a deployed URL alone do not submit the project.

For field-by-field, paste-ready answers to the GOMYCODE form, including prize fit, tool disclosure, testing, and responsible-AI responses, see [GOMYCODE_FORM_ANSWERS.md](./GOMYCODE_FORM_ANSWERS.md).

## Project title

HakiScribe — conversation to reviewed legal work

## Project summary (145 words)

HakiScribe helps Kenyan legal professionals turn spoken client meetings, chambers discussions, and hearings into reviewed legal work. A lawyer, clerk, or judge records through a phone, laptop microphone, or Omi wearable and can flag a date, admission, or contract term without stopping the conversation. After the room, the user names speakers and marks privileged or off-record lines before AI analysis. HakiScribe then proposes source-traceable work such as editable letters, hearing dates, private notes, matters, contacts, time entries, and research prompts. The user reviews every proposed action and decides what to generate or export. The prototype supports African-language and English code-switched sessions through Sahara refinement when connected. HakiScribe does not provide legal advice or send documents automatically. Its production path adds verified accounts, firm workspaces, MFA, and tenant-scoped records for real legal practice.

## Problem, solution, and key features

**Problem:** Spoken legal work becomes unreliable paperwork when professionals reconstruct it from memory after a meeting or hearing. A raw transcript leaves them with more reading, not the next piece of work.

**Solution:** HakiScribe keeps the conversation as the source of truth and turns verified, non-redacted speech into selected, editable legal-work artifacts.

**Key features:**

- Microphone and Omi capture with a no-look flag for important moments.
- Speaker naming and reversible privileged/off-record controls before AI processing.
- Code-switch-aware transcription and optional Intron Sahara legal refinement.
- Source-traceable Action Tray for drafts, dates, notes, matters, contacts, time, and research.
- Human review before generation, export, or sending.
- Production architecture for verified identity, firms, MFA, and tenant isolation.

## Technologies used

- React, TanStack Start, Vite, Tailwind CSS
- FastAPI and WebSockets
- OpenRouter / OpenAI-compatible models for speech and drafting
- Intron Sahara for supported African-language and code-switched speech refinement
- Trigger.dev for optional durable background workflows
- Exa for research context
- Omi wearable workflows
- Supabase Auth and Postgres/RLS production foundation

## Transparent AI and tool disclosure

HakiScribe uses AI for speech transcription, action detection, draft generation, and optional research context. It separates privileged/redacted transcript lines before detection and drafting. Users review proposed outputs, and the product does not send legal advice or documents automatically. OpenRouter/OpenAI-compatible models, Intron Sahara, Exa, Trigger.dev, Omi, and optional NVIDIA NIM are integrated or supported as documented in the repository. NVIDIA Brev was **not used** unless the final team actually uses it during this event; if that changes, update this statement to identify the exact Brev workload, model, and fallback. No API keys, passwords, or voucher codes belong in the form, video, slides, or repository.

## Prize direction

**Primary recommendation:** GOMYCODE × NVIDIA Real-World AI Impact Award / Kenya country podium.

HakiScribe addresses a practical Kenyan legal-work problem: preserving accurate spoken records and reducing administrative delay for advocates, clerks, and chambers. The working prototype demonstrates AI only where it supports a reviewable workflow, with privacy, privilege, human oversight, and code-switching needs made explicit.

**Additional eligible option:** Click Mobile Mobile-First Impact Award.

The mobile-first capture flow is designed for practical Kenyan legal rooms, allowing a user to record and flag moments from a phone while maintaining attention in the conversation. The video should show this mobile capture flow, followed by speaker/privilege review and a selected output.

## 90-second demo plan

1. **0–12 seconds — problem:** “A legal meeting ends, and the important detail lives in memory.” Show the landing page and open a session.
2. **12–32 seconds — capture:** Record or show the completed judge demo. Flag a date or admission.
3. **32–50 seconds — trust:** Name speakers and mark one privileged/off-record line. State that it is excluded from AI work.
4. **50–72 seconds — AI proof:** Open the Action Tray. Show a source line for one proposed action and select a draft or calendar item.
5. **72–90 seconds — result:** Show the editable output, then close with the mobile/legal impact and human-review rule.

## Final form checklist

- [ ] Use the final confirmed team name and lead email.
- [ ] Select Kenya and the confirmed participation mode.
- [ ] Keep the project summary at 150 words or fewer.
- [ ] Upload the deck and paste a public view-only URL.
- [ ] Confirm the YouTube video is public or unlisted and no longer than 90 seconds.
- [ ] Open all three URLs in a private browser window.
- [ ] Select only prizes for which the project is eligible and add the matching evidence above.
- [ ] State every model, API, dataset, generated asset, limitation, fallback, and actual NVIDIA Brev use honestly.
- [ ] Save the Google Form confirmation after submitting by 17:30 Tunis time (19:30 Kenya time).

## Notes for reviewers

- Live app: https://hakiscribe.lovable.app
- Demo video: https://youtu.be/FjsZqMBsCfs
- Source code: https://github.com/Isomkevin/haki-scribe
- Product guide: `../PRODUCT_GUIDE.md`
- Production readiness: `../PRODUCTION_READINESS.md`
