"""Required legal-term / named-entity hit rate for benchmark clips."""

from __future__ import annotations


def _fold(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace())


def entity_accuracy(reference_terms: list[str], hypothesis: str) -> float:
    """Fraction of required terms found in the hypothesis (case-insensitive)."""
    if not reference_terms:
        return 1.0
    folded = _fold(hypothesis)
    hits = sum(1 for term in reference_terms if _fold(term) in folded)
    return hits / len(reference_terms)
