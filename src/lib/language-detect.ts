/**
 * Heuristic language-mix detection for Kenyan legal speech.
 * Used live in RecordingScreen to decide Sahara refine + show a badge.
 * Indicative lexicon cues — not a full LID model.
 */

const SW_MARKERS = new Set([
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
]);

const EN_MARKERS = new Set([
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
]);

const OTHER_HINTS = new Set([
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
  "sannu",
  "nagode",
  "lahiya",
  "gaskiya",
  "alkali",
  "jowo",
  "sawubona",
  "ngiyabonga",
  "inkantolo",
  "muraho",
  "murakoze",
  "webale",
  "abi",
  "wetin",
  "dey",
  "una",
]);

export type DetectedLanguageMode = "en" | "sw" | "code-switch" | "multilingual" | "unknown";

export interface LanguageMixResult {
  mode: DetectedLanguageMode;
  enHits: number;
  swHits: number;
  otherHits: number;
  tokenCount: number;
  confidence: number;
  reason: string;
}

function tokens(text: string): string[] {
  return (text.match(/[A-Za-zÀ-ÖØ-öø-ÿ']+/g) ?? []).map((t) => t.toLowerCase());
}

export function detectLanguageMix(text: string): LanguageMixResult {
  const toks = tokens(text);
  if (!toks.length) {
    return { mode: "unknown", enHits: 0, swHits: 0, otherHits: 0, tokenCount: 0, confidence: 0, reason: "empty transcript" };
  }

  let en = 0;
  let sw = 0;
  let other = 0;
  for (const t of toks) {
    if (EN_MARKERS.has(t)) en += 1;
    if (SW_MARKERS.has(t)) sw += 1;
    if (OTHER_HINTS.has(t)) other += 1;
  }
  if (/[\u1200-\u137F\u0600-\u06FF]/.test(text)) other += 3;

  const n = toks.length;
  const enR = en / n;
  const swR = sw / n;

  if (other >= 2 || (other >= 1 && (en >= 1 || sw >= 1))) {
    return {
      mode: "multilingual",
      enHits: en,
      swHits: sw,
      otherHits: other,
      tokenCount: n,
      confidence: Math.min(1, 0.45 + 0.15 * other),
      reason: "non-EN/SW language cues",
    };
  }

  if (en >= 2 && sw >= 2) {
    return {
      mode: "code-switch",
      enHits: en,
      swHits: sw,
      otherHits: other,
      tokenCount: n,
      confidence: Math.min(1, 0.5 + 0.1 * Math.min(en, sw)),
      reason: "English and Kiswahili markers",
    };
  }

  if (swR >= 0.08 && sw >= 2 && en <= 1) {
    return {
      mode: "sw",
      enHits: en,
      swHits: sw,
      otherHits: other,
      tokenCount: n,
      confidence: Math.min(1, 0.4 + swR),
      reason: "mostly Kiswahili",
    };
  }

  if (enR >= 0.08 && en >= 2 && sw <= 1) {
    return {
      mode: "en",
      enHits: en,
      swHits: sw,
      otherHits: other,
      tokenCount: n,
      confidence: Math.min(1, 0.4 + enR),
      reason: "mostly English",
    };
  }

  if (en >= 1 && sw >= 1) {
    return {
      mode: "code-switch",
      enHits: en,
      swHits: sw,
      otherHits: other,
      tokenCount: n,
      confidence: 0.55,
      reason: "mixed EN/SW markers",
    };
  }

  if (sw > en && sw >= 1) {
    return { mode: "sw", enHits: en, swHits: sw, otherHits: other, tokenCount: n, confidence: 0.35, reason: "weak Kiswahili signal" };
  }
  if (en > sw && en >= 1) {
    return { mode: "en", enHits: en, swHits: sw, otherHits: other, tokenCount: n, confidence: 0.35, reason: "weak English signal" };
  }

  return {
    mode: "unknown",
    enHits: en,
    swHits: sw,
    otherHits: other,
    tokenCount: n,
    confidence: 0,
    reason: "insufficient language signal",
  };
}

export function needsSaharaRefine(
  languageHint: string | null | undefined,
  detectedMode?: DetectedLanguageMode | null,
): boolean {
  // Lazy import avoided — duplicate of workspace-settings.usesSaharaRefine for tree purity.
  const pairs = new Set([
    "code-switch",
    "multilingual",
    "en-sw",
    "en-ha",
    "en-yo",
    "en-ig",
    "en-zu",
    "en-xh",
    "en-rw",
    "en-lg",
    "en-pcm",
    "fr-rw",
  ]);
  const africanMono = new Set(["sw", "ha", "yo", "ig", "zu", "xh", "rw", "lg", "pcm", "am", "fr"]);
  if (languageHint && (pairs.has(languageHint) || africanMono.has(languageHint))) return true;
  return detectedMode === "code-switch" || detectedMode === "multilingual";
}

export function detectedModeLabel(mode: DetectedLanguageMode): string | null {
  if (mode === "code-switch") return "Code-switching detected — Sahara will refine on Stop";
  if (mode === "multilingual") return "Multilingual speech detected — Sahara will refine on Stop";
  return null;
}
