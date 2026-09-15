"""Levenshtein-based WER and CER — no external deps."""

from __future__ import annotations


def _levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _normalize_words(text: str) -> list[str]:
    return [part for part in "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower()).split() if part]


def _normalize_chars(text: str) -> list[str]:
    return [ch for ch in text.lower() if ch.isalnum()]


def wer(reference: str, hypothesis: str) -> float:
    ref = _normalize_words(reference)
    hyp = _normalize_words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref = _normalize_chars(reference)
    hyp = _normalize_chars(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)
