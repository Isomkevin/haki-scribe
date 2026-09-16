"""Session language hints for HakiScribe × Sahara.

Beyond English / Kiswahili: African monolingual codes and bilingual
pairs that map to Intron Sahara ``use_language_asr_input`` values.
See https://docs.voice.intron.io/docs/stt/supported-languages
"""

from __future__ import annotations

from typing import Optional

# Monolingual ISO-ish codes we expose (subset of Sahara-supported).
MONOLINGUAL: dict[str, str] = {
    "en": "English",
    "sw": "Kiswahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "zu": "Zulu",
    "xh": "Xhosa",
    "rw": "Kinyarwanda",
    "lg": "Luganda",
    "pcm": "Nigerian Pidgin",
    "fr": "French",
    "am": "Amharic",
}

# Bilingual / code-switch session hints → primary Sahara ASR code.
# Prefer the African language code so English-forced decoding does not
# erase African tokens (same rationale as EN–SW → sw).
PAIR_TO_SAHARA: dict[str, str] = {
    "code-switch": "sw",  # legacy Kenyan EN–SW
    "en-sw": "sw",
    "en-ha": "ha",
    "en-yo": "yo",
    "en-ig": "ig",
    "en-zu": "zu",
    "en-xh": "xh",
    "en-rw": "rw",
    "en-lg": "lg",
    "en-pcm": "pcm",
    "fr-rw": "rw",  # Sahara trilingual KW/EN/FR family — primary African code
    "multilingual": "sw",  # open African mix; default toward East Africa
}

PAIR_LABELS: dict[str, str] = {
    "code-switch": "English + Kiswahili",
    "en-sw": "English + Kiswahili",
    "en-ha": "English + Hausa",
    "en-yo": "English + Yoruba",
    "en-ig": "English + Igbo",
    "en-zu": "English + Zulu",
    "en-xh": "English + Xhosa",
    "en-rw": "English + Kinyarwanda",
    "en-lg": "English + Luganda",
    "en-pcm": "English + Nigerian Pidgin",
    "fr-rw": "French + Kinyarwanda",
    "multilingual": "Multilingual / African code-switch",
}


def label_for(language_hint: Optional[str]) -> str:
    if not language_hint:
        return "Unknown"
    if language_hint in PAIR_LABELS:
        return PAIR_LABELS[language_hint]
    if language_hint in MONOLINGUAL:
        return MONOLINGUAL[language_hint]
    return language_hint


def is_pair_or_multilingual(language_hint: Optional[str]) -> bool:
    return language_hint in PAIR_TO_SAHARA


def is_african_monolingual(language_hint: Optional[str]) -> bool:
    return bool(language_hint) and language_hint in MONOLINGUAL and language_hint not in ("en",)


def uses_sahara_refine(language_hint: Optional[str]) -> bool:
    """Explicit session modes that should refine with Sahara when keyed."""
    if not language_hint:
        return False
    if is_pair_or_multilingual(language_hint):
        return True
    # Non-English African monolingual — Sahara is the stronger African ASR.
    return is_african_monolingual(language_hint)


def sahara_asr_code(language_hint: Optional[str]) -> str:
    if not language_hint:
        return "en"
    if language_hint in PAIR_TO_SAHARA:
        return PAIR_TO_SAHARA[language_hint]
    if language_hint in MONOLINGUAL:
        return language_hint
    # Detected modes from language_detect
    if language_hint == "code-switch":
        return "sw"
    return "en"


def whisper_iso_language(language_hint: Optional[str]) -> Optional[str]:
    """Whisper only gets a forced ISO code for clear monolingual sessions."""
    if language_hint in ("en", "sw", "fr", "ha", "yo", "ig", "zu", "xh", "rw", "lg", "am"):
        # Whisper may ignore unsupported codes; still pass common ones.
        return language_hint if language_hint in ("en", "sw", "fr") else None
    return None


def whisper_code_switch_prompt(language_hint: Optional[str]) -> Optional[str]:
    if not language_hint:
        return None
    if language_hint in ("code-switch", "en-sw"):
        return (
            "This conversation mixes Kenyan English and Kiswahili, including code-switching. "
            "Transcribe both languages faithfully. Do not translate."
        )
    if language_hint == "en-ha":
        return "This conversation mixes English and Hausa. Transcribe both faithfully. Do not translate."
    if language_hint == "en-yo":
        return "This conversation mixes English and Yoruba. Transcribe both faithfully. Do not translate."
    if language_hint == "en-ig":
        return "This conversation mixes English and Igbo. Transcribe both faithfully. Do not translate."
    if language_hint == "en-zu":
        return "This conversation mixes English and Zulu. Transcribe both faithfully. Do not translate."
    if language_hint == "en-xh":
        return "This conversation mixes English and Xhosa. Transcribe both faithfully. Do not translate."
    if language_hint == "en-rw":
        return "This conversation mixes English and Kinyarwanda. Transcribe both faithfully. Do not translate."
    if language_hint == "en-lg":
        return "This conversation mixes English and Luganda. Transcribe both faithfully. Do not translate."
    if language_hint == "en-pcm":
        return "This conversation mixes English and Nigerian Pidgin. Transcribe both faithfully. Do not translate."
    if language_hint == "fr-rw":
        return (
            "This conversation mixes French, English, and/or Kinyarwanda. "
            "Transcribe faithfully without translating."
        )
    if language_hint == "multilingual":
        return (
            "This conversation may mix English with one or more African languages "
            "(code-switching). Transcribe all languages faithfully. Do not translate."
        )
    return None
