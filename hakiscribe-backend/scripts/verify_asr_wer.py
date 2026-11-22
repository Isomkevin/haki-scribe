#!/usr/bin/env python3
"""WER harness for EN/SW ASR. Skips unless HAKISCRIBE_VERIFY_ASR=1."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _wer(ref: str, hyp: str) -> float:
    r = ref.lower().split()
    h = hyp.lower().split()
    if not r:
        return 0.0 if not h else 1.0
    # Levenshtein on tokens
    dp = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        dp[i][0] = i
    for j in range(len(h) + 1):
        dp[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[-1][-1] / len(r)


async def main() -> int:
    if os.environ.get("HAKISCRIBE_VERIFY_ASR", "").lower() not in ("1", "true", "yes"):
        print("SKIP: set HAKISCRIBE_VERIFY_ASR=1 to run (requires Whisper/Intron + samples)")
        return 0

    from app.services import ai_mode, transcription

    samples_dir = Path(os.environ.get("HAKISCRIBE_ASR_SAMPLES_DIR") or "")
    pairs: list[tuple[Path, str, str]] = []
    if samples_dir.is_dir():
        for wav in sorted(samples_dir.glob("*.wav")):
            ref_path = wav.with_suffix(".txt")
            if ref_path.exists():
                lang = "sw" if "sw" in wav.stem.lower() else "en"
                pairs.append((wav, ref_path.read_text(encoding="utf-8").strip(), lang))
    if not pairs:
        print("SKIP: no wav+txt pairs in HAKISCRIBE_ASR_SAMPLES_DIR")
        return 0

    name = ai_mode.resolve_asr_provider_name()
    provider = transcription._provider_for_name(name)
    print(f"ASR provider: {name}")
    for wav, ref, lang in pairs:
        data = wav.read_bytes()
        if hasattr(provider, "transcribe_file"):
            result = await provider.transcribe_file(data, filename=wav.name, language_hint=lang)
            hyp = result.text
        else:
            result = await provider.transcribe_chunk(data, lang)
            hyp = result.text
        score = _wer(ref, hyp)
        print(f"{wav.name} lang={lang} WER={score:.3f}")
        print(f"  REF: {ref[:120]}")
        print(f"  HYP: {hyp[:120]}")
    print("Record these WER lines in docs/engineering/hakiscribe-resilience/09-testing-and-verification.md (1B).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
