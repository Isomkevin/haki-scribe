"""Heuristic language-mix detection for Kenyan legal speech.

Used to decide when to refine with Intron Sahara after a Whisper live pass.
This is indicative (lexicon + script cues), not a full LID model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# High-signal Kiswahili / Sheng / Kenyan legal function words and stems.
_SW_MARKERS = frozenset(
    {
        "mheshimiwa",
        "mahakama",
        "amri",
        "mteja",
        "hatutaki",
        "kucheleweshwa",
        "tafadhali",
        "niko",
        "hapa",
        "kuzungumzia",
        "nataka",
        "jua",
        "kama",
        "tunaweza",
        "hii",
        "ni",
        "ya",
        "na",
        "kwa",
        "katika",
        "sasa",
        "leo",
        "kesho",
        "jana",
        "asante",
        "karibu",
        "pole",
        "samahani",
        "habari",
        "mzuri",
        "sawa",
        "ndiyo",
        "hapana",
        "bwana",
        "bibi",
        "dada",
        "kaka",
        "mama",
        "baba",
        "watoto",
        "pesa",
        "malipo",
        "mkataba",
        "kesi",
        "wakili",
        "jaji",
        "ushahidi",
        "dai",
        "mshtakiwa",
        "mlalamikaji",
        "inafuata",
        "anahitaji",
        "kuelewa",
        "amelipa",
        "inatumiwa",
        "inachukua",
        "kutengeneza",
        "sio",
        "siyo",
        "tu",
        "pia",
        "lakini",
        "kwaajili",
        "kwa",
        "ajili",
        "wenye",
        "yake",
        "yangu",
        "yetu",
        "wao",
        "hao",
        "huyo",
        "huyu",
        "ile",
        "haya",
        "hayo",
        "bado",
        "tayari",
        "sana",
        "kidogo",
        "mingi",
        "mengi",
    }
)

_EN_MARKERS = frozenset(
    {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "court",
        "hearing",
        "plaintiff",
        "defendant",
        "counsel",
        "application",
        "dismissed",
        "adjourned",
        "costs",
        "matter",
        "lease",
        "agreement",
        "employment",
        "notice",
        "salary",
        "request",
        "within",
        "thirty",
        "days",
        "bail",
        "cash",
        "surety",
        "mention",
        "tuesday",
        "friday",
        "deposit",
        "receipt",
        "update",
        "draft",
        "letter",
        "privilege",
        "shareholder",
        "discussion",
        "record",
        "orders",
        "parties",
        "directed",
        "submissions",
        "fourteen",
        "company",
        "terminated",
        "without",
        "three",
        "months",
        "owe",
        "february",
        "march",
        "civil",
        "suit",
        "versus",
        "limited",
        "enterprises",
        "holdings",
        "under",
        "signed",
        "april",
        "o'clock",
        "forenoon",
        "conditional",
        "release",
        "discharge",
        "client",
        "confirm",
        "before",
        "also",
        "flag",
        "off",
    }
)

# Tokens that often appear in other African languages / non-Latin scripts → multilingual.
_OTHER_HINTS = frozenset(
    {
        "yoruba",
        "hausa",
        "igbo",
        "kinyarwanda",
        "luganda",
        "zulu",
        "xhosa",
        "amharic",
        "wolof",
        "twi",
        "akan",
        "fulani",
        "pidgin",
        "bonjour",
        "merci",
        "s'il",
        "vous",
        "n'est",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


@dataclass
class LanguageMixResult:
    mode: str  # "en" | "sw" | "code-switch" | "multilingual" | "unknown"
    en_hits: int
    sw_hits: int
    other_hits: int
    token_count: int
    confidence: float
    reason: str


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


def detect_language_mix(text: str) -> LanguageMixResult:
    tokens = _tokens(text)
    if not tokens:
        return LanguageMixResult("unknown", 0, 0, 0, 0, 0.0, "empty transcript")

    en = sum(1 for t in tokens if t in _EN_MARKERS)
    sw = sum(1 for t in tokens if t in _SW_MARKERS)
    other = sum(1 for t in tokens if t in _OTHER_HINTS)
    # Non-Latin / Ethiopic / Arabic script → treat as multilingual African speech.
    if re.search(r"[\u1200-\u137F\u0600-\u06FF\u0100-\u024F]", text or ""):
        other += 3

    n = len(tokens)
    en_r = en / n
    sw_r = sw / n

    if other >= 2 or (other >= 1 and (en >= 1 or sw >= 1)):
        conf = min(1.0, 0.45 + 0.15 * other)
        return LanguageMixResult("multilingual", en, sw, other, n, conf, "non-EN/SW language cues")

    # Need a few content tokens before calling code-switch (avoid early false positives).
    if en >= 2 and sw >= 2:
        conf = min(1.0, 0.5 + 0.1 * min(en, sw))
        return LanguageMixResult("code-switch", en, sw, other, n, conf, "English and Kiswahili markers")

    if sw_r >= 0.08 and sw >= 2 and en <= 1:
        return LanguageMixResult("sw", en, sw, other, n, min(1.0, 0.4 + sw_r), "mostly Kiswahili")

    if en_r >= 0.08 and en >= 2 and sw <= 1:
        return LanguageMixResult("en", en, sw, other, n, min(1.0, 0.4 + en_r), "mostly English")

    if en >= 1 and sw >= 1:
        return LanguageMixResult("code-switch", en, sw, other, n, 0.55, "mixed EN/SW markers")

    if sw > en and sw >= 1:
        return LanguageMixResult("sw", en, sw, other, n, 0.35, "weak Kiswahili signal")
    if en > sw and en >= 1:
        return LanguageMixResult("en", en, sw, other, n, 0.35, "weak English signal")

    return LanguageMixResult("unknown", en, sw, other, n, 0.0, "insufficient language signal")


def needs_sahara_refine(
    language_hint: Optional[str],
    *,
    detected_mode: Optional[str] = None,
    transcript_text: Optional[str] = None,
) -> bool:
    """True when user opted in OR live captions look code-switched / multilingual."""
    if language_hint in ("code-switch", "multilingual"):
        return True
    mode = detected_mode
    if mode is None and transcript_text is not None:
        mode = detect_language_mix(transcript_text).mode
    return mode in ("code-switch", "multilingual")


def effective_language_hint(
    language_hint: Optional[str],
    *,
    detected_mode: Optional[str] = None,
    transcript_text: Optional[str] = None,
) -> Optional[str]:
    """Prefer explicit multilingual/code-switch; else promote detected mix for Sahara."""
    if language_hint in ("code-switch", "multilingual"):
        return language_hint
    mode = detected_mode
    if mode is None and transcript_text is not None:
        mode = detect_language_mix(transcript_text).mode
    if mode in ("code-switch", "multilingual"):
        return mode
    return language_hint
