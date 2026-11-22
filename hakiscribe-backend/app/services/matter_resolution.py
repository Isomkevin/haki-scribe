"""Confidence-based matter matching for virtual hearings.

Never silently attaches when confidence is ambiguous — callers must require
human confirmation below CONFIRM_THRESHOLD.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.models.schemas import Matter

# Auto-suggest OK at or above this score; still surface candidates for review.
AUTO_MATCH_THRESHOLD = 0.85
# Below this, status becomes pending_confirm (human required).
CONFIRM_THRESHOLD = 0.85
# Top two candidates closer than this are ambiguous (e.g. one client, two suits).
AMBIGUITY_MARGIN = 0.1
# Multiplier when hearing and matter carry different case numbers.
CONFLICT_PENALTY = 0.4

# Kenyan registry style: "E123 of 2024", "HCCC No. E123 of 2024", "45/2023", "E045/2024".
FULL_REF_RE = re.compile(
    r"\b(?:([A-Za-z])\s?)?0*(\d{1,6})\s*(?:of|/)\s*((?:19|20)\d{2})\b",
    re.I,
)

CASE_REF_RE = re.compile(
    r"\b(?:case|matter|cause|suit|petition|misc\.?|civil|criminal)"
    r"(?:\s*(?:no\.?|number|#|:))?\s*([A-Za-z]*\d[\w/.\-]*)",
    re.I,
)


def extract_case_reference(*texts: Optional[str]) -> Optional[str]:
    for text in texts:
        if not text:
            continue
        m = CASE_REF_RE.search(text)
        if m:
            return m.group(1).strip()
    return None


def canonical_case_refs(*texts: Optional[str]) -> set[str]:
    """Canonical "PREFIX+NUMBER/YEAR" refs, e.g. "HCCC No. E045 of 2024" → {"E45/2024"}.

    Court-division prefixes (HCCC, ELRC, …) are dropped; only the single
    registry letter (E/F/…) before the number is kept, since that is what varies.
    """
    refs: set[str] = set()
    for text in texts:
        for m in FULL_REF_RE.finditer(text or ""):
            refs.add(f"{(m.group(1) or '').upper()}{int(m.group(2))}/{m.group(3)}")
    return refs


def _contains_token(haystack: str, needle: str) -> bool:
    """Boundary-aware containment so ref "12" does not match "120/2023"."""
    if not needle:
        return False
    return re.search(rf"(?<![\w]){re.escape(needle)}(?![\w])", haystack) is not None


def _norm(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", a))
    tb = set(re.findall(r"[a-z0-9]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def score_matter(
    matter: Matter,
    *,
    title: str = "",
    description: str = "",
    case_reference: Optional[str] = None,
    starts_at: Optional[datetime] = None,
) -> tuple[float, str]:
    """Return (score 0..1, rationale)."""
    reasons: list[str] = []
    score = 0.0

    hay = _norm(f"{title} {description}")
    client = _norm(matter.client_name)
    mname = _norm(matter.matter_name)
    ref = _norm(case_reference or extract_case_reference(title, description) or "")

    hearing_refs = canonical_case_refs(case_reference, title, description)
    matter_refs = canonical_case_refs(matter.matter_name, matter.client_name)
    conflict = bool(hearing_refs and matter_refs and not (hearing_refs & matter_refs))

    if hearing_refs & matter_refs:
        score += 0.55
        reasons.append(f"case reference match ({', '.join(sorted(hearing_refs & matter_refs))})")
    elif not conflict and ref and _contains_token(mname, ref):
        score += 0.55
        reasons.append(f"case reference overlap ({ref})")
    elif not conflict and ref and _contains_token(hay, ref) and _contains_token(client, ref):
        score += 0.45
        reasons.append(f"case reference in hearing text ({ref})")

    if client and client in hay:
        score += 0.3
        reasons.append(f"client name in hearing ({matter.client_name})")
    else:
        overlap = _token_overlap(client, hay)
        if overlap >= 0.4:
            score += 0.2 * overlap
            reasons.append(f"client token overlap ({overlap:.2f})")

    if mname and mname in hay:
        score += 0.25
        reasons.append(f"matter name in hearing ({matter.matter_name})")
    else:
        overlap = _token_overlap(mname, hay)
        if overlap >= 0.35:
            score += 0.15 * overlap
            reasons.append(f"matter token overlap ({overlap:.2f})")

    # Soft time prior: hearings without date do not lose score.
    if starts_at is not None:
        reasons.append(f"hearing time {starts_at.isoformat()}")

    if conflict:
        score *= CONFLICT_PENALTY
        reasons.append(
            f"case reference conflict (hearing {', '.join(sorted(hearing_refs))} "
            f"vs matter {', '.join(sorted(matter_refs))})"
        )

    score = min(1.0, score)
    rationale = "; ".join(reasons) if reasons else "no strong overlap"
    return score, rationale


def propose_matches(
    matters: list[Matter],
    *,
    title: str = "",
    description: str = "",
    case_reference: Optional[str] = None,
    starts_at: Optional[datetime] = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for matter in matters:
        s, rationale = score_matter(
            matter,
            title=title,
            description=description,
            case_reference=case_reference,
            starts_at=starts_at,
        )
        if s <= 0:
            continue
        scored.append(
            {
                "matter_id": str(matter.id),
                "client_name": matter.client_name,
                "matter_name": matter.matter_name,
                "score": round(s, 4),
                "rationale": rationale,
                "requires_confirmation": s < CONFIRM_THRESHOLD,
            }
        )
    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:limit]


def best_match(candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not candidates:
        return None
    top = candidates[0]
    if float(top["score"]) < AUTO_MATCH_THRESHOLD:
        return None
    if is_ambiguous(candidates):
        return None
    return top


def is_ambiguous(candidates: list[dict[str, Any]]) -> bool:
    """Two near-equal top candidates — a human must pick, whatever the score."""
    if len(candidates) < 2:
        return False
    return float(candidates[0]["score"]) - float(candidates[1]["score"]) < AMBIGUITY_MARGIN


def requires_human_confirmation(candidates: list[dict[str, Any]]) -> bool:
    top = best_match(candidates)
    if top is None:
        return True
    return False
