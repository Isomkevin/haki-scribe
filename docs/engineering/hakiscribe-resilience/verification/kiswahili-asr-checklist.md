# Kiswahili ASR verification checklist

## Models / paths

| Path | When | Notes |
| --- | --- | --- |
| Local Whisper `small` | Default Compose | Measured WER on FLEURS ~0.66 — not court-ready |
| Local Whisper `large-v3` | `WHISPER_MODEL=large-v3` (≥3 GB) | Target for legal EN/SW |
| Intron Sahara | Hybrid + Intron connector | Prefer for Kiswahili when hybrid allowed |

## Harness

```bash
set HAKISCRIBE_VERIFY_ASR=1
set HAKISCRIBE_ASR_SAMPLES_DIR=path\to\wavs   # optional; else synthetic
python scripts/verify_asr_wer.py
```

Tracker language selector: **Kiswahili (`sw`)** → `language_hint=sw` on `/process`.

## Checklist

- [ ] EN sample WER recorded (baseline)
- [ ] SW sample WER with `language=sw` recorded
- [ ] SW auto-detect does not pick non-`en`/`sw` languages
- [ ] Legal prompt not echoed into transcript
- [ ] Hybrid Intron path exercised when credentials present
- [ ] Results pasted into `09` (pass/fail + WER) — **not verified** until 1B audio exists
