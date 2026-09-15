# Responsible AI — HakiScribe (Sahara CodeSwitch submission)

## Consent

Today, HakiScribe requests **browser microphone permission** before recording. There is **not yet** a dedicated in-app notice that all parties to a conversation have consented to recording — this is a **known gap** we treat as required before production deployment in courtrooms and client meetings. For benchmark clips and demo recordings, speakers must give **explicit consent**; we do not use real client matter audio in the public repo.

## Privilege and off-record speech

HakiScribe includes a **privilege / off-record control**: transcript segments can be marked redacted before any language model sees them. Redacted lines remain visible to the user (struck through) but are **excluded from detection and generation**. This is implemented today and should be shown in any demo involving sensitive speech.

## Data handling

- **Sessions and transcripts** are stored in the workspace backend (Postgres when `DATABASE_URL` is set, otherwise local JSON snapshot on the server).
- **Full mic recordings** for Sahara refine are uploaded on Stop and processed by Intron's API; they are **not** durably archived in HakiScribe by default (ephemeral upload for transcription).
- HakiChain is building toward **Kenya Data Protection Act 2019** alignment (lawful basis, retention limits, processor agreements). That compliance program is **in progress** — we do not claim full DPA certification yet.

## Bias and evaluation fairness

Benchmark clips are a **small, consented sample** (templates in-repo; audio recorded locally). Comparisons between Sahara and global Whisper models are **indicative**, not a comprehensive evaluation of every African language pair Sahara supports. We report WER/CER and required legal-term accuracy transparently and avoid overclaiming from n≈6 clips.

**Automatic language detection** in-product uses a **lexicon heuristic** on live Whisper captions (English / Kiswahili / mix cues). It can miss rare languages or false-positive early in a recording; Sahara refine still requires the Intron connector and can be forced via the Multilingual / English+Kiswahili session options.

## Safety

- Generated drafts require **human review** before leaving the desk (Action Tray is selective, not auto-send).
- API keys (Intron, OpenRouter, etc.) stay **server-side** in connector storage; the UI shows masked hints only.

Contact: voice@intron.io for Sahara API issues; HakiChain for product privacy questions.
