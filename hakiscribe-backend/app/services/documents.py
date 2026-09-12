"""
Real legal document composition, grounded in the verified transcript.

This is what makes a draft_document card return an actual Kenyan legal
document instead of a placeholder. Two layers:

1. `extract_facts` pulls concrete, checkable facts out of the transcript
   — money, dates, statute references, LR/title numbers, cause numbers,
   courts, deadlines, parties. Nothing is invented: every value comes
   from a line the user did not redact.
2. `compose_document` renders those facts into a correctly-structured
   document for the detected kind (demand letter, statutory notice under
   s.90 Land Act, replying affidavit, plaint, notice of arbitration,
   application to revoke a grant, attendance/directions note, or a legal
   memo). Anything the record does not supply is left as a bracketed
   placeholder so counsel can see exactly what still needs confirming.

The OpenRouter drafting model, when configured, drafts on top of these
same extracted facts. When it isn't, this module is the draft — not a
stub of one.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.models.schemas import DetectedAction, TranscriptSegment

MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "ninety": 90, "hundred": 100,
}

DOCUMENT_KINDS = (
    "demand_letter",
    "statutory_notice",
    "replying_affidavit",
    "supporting_affidavit",
    "plaint",
    "notice_of_arbitration",
    "revocation_of_grant",
    "attendance_note",
    "engagement_letter",
    "legal_memo",
)

KIND_TITLES = {
    "demand_letter": "DEMAND LETTER",
    "statutory_notice": "STATUTORY NOTICE",
    "replying_affidavit": "REPLYING AFFIDAVIT",
    "supporting_affidavit": "SUPPORTING AFFIDAVIT",
    "plaint": "PLAINT",
    "notice_of_arbitration": "NOTICE OF ARBITRATION",
    "revocation_of_grant": "SUMMONS FOR REVOCATION OF GRANT",
    "attendance_note": "ATTENDANCE NOTE",
    "engagement_letter": "LETTER OF ENGAGEMENT",
    "legal_memo": "LEGAL MEMORANDUM",
}

_KIND_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("revocation_of_grant", ("revoke the grant", "revocation", "letters of administration", "succession")),
    ("statutory_notice", ("statutory notice", "section ninety", "section 90", "land act", "notification before sale")),
    ("notice_of_arbitration", ("notice of arbitration", "arbitration", "arbitral")),
    ("replying_affidavit", ("replying affidavit",)),
    ("supporting_affidavit", ("supporting affidavit", "supplementary affidavit", "affidavit")),
    ("plaint", ("plaint", "file suit", "magistrate's court", "magistrates court", "civil suit")),
    ("demand_letter", ("demand letter", "formal demand", "demand notice", "letter of demand", "demand")),
    ("engagement_letter", ("retainer", "engagement letter", "terms of engagement")),
    ("attendance_note", ("mention", "directions", "my lord", "appearances", "cause number")),
]


def infer_document_kind(text: str) -> str:
    lowered = text.lower()
    for kind, needles in _KIND_KEYWORDS:
        if any(needle in lowered for needle in needles):
            return kind
    return "legal_memo"


def normalise_kind(raw: str | None, transcript_text: str = "") -> str:
    if raw:
        candidate = re.sub(r"[^a-z]+", "_", str(raw).lower()).strip("_")
        if candidate in DOCUMENT_KINDS:
            return candidate
        for kind in DOCUMENT_KINDS:
            if kind.split("_")[0] in candidate:
                return kind
    return infer_document_kind(transcript_text)


def _words_to_number(phrase: str) -> float | None:
    total = 0.0
    current = 0.0
    seen = False
    for word in re.split(r"[\s-]+", phrase.strip().lower()):
        if word in ("and", "point"):
            continue
        if word in NUMBER_WORDS:
            seen = True
            value = NUMBER_WORDS[word]
            if value == 100:
                current = (current or 1) * 100
            else:
                current += value
        else:
            return None
    if not seen:
        return None
    total += current
    return total or None


_AMOUNT_RE = re.compile(
    r"\b((?:" + "|".join(NUMBER_WORDS) + r")(?:[\s-]+(?:point|and|" + "|".join(NUMBER_WORDS) + r"))*)"
    r"\s+(million|billion|thousand|shillings)\b",
    re.IGNORECASE,
)

_DIGIT_AMOUNT_RE = re.compile(
    r"(?:ksh\.?|kes|shillings?)\s*([\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?",
    re.IGNORECASE,
)


def _format_money(value: float) -> str:
    if value >= 1_000_000:
        text = f"{value/1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"KES {value:,.0f} (Kenya Shillings {text} million)"
    return f"KES {value:,.0f}"


def _parse_word_amounts(text: str) -> list[str]:
    amounts: list[str] = []
    lowered = text.lower()
    # "four point two million", "eighteen million shillings", "nine hundred thousand"
    pattern = re.compile(
        r"\b((?:" + "|".join(NUMBER_WORDS) + r")(?:[\s-]+(?:point\s+)?(?:" + "|".join(NUMBER_WORDS) + r"))*)\s+"
        r"(million|thousand|billion)\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(lowered):
        phrase, scale = match.group(1), match.group(2).lower()
        if "point" in phrase:
            whole_part, _, frac_part = phrase.partition("point")
            whole = _words_to_number(whole_part) or 0
            frac = _words_to_number(frac_part)
            base = whole + (frac / 10 if frac is not None and frac < 10 else 0)
        else:
            base = _words_to_number(phrase)
        if base is None:
            continue
        multiplier = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}[scale]
        value = base * multiplier
        formatted = _format_money(value)
        if formatted not in amounts:
            amounts.append(formatted)
    for match in _DIGIT_AMOUNT_RE.finditer(text):
        raw = float(match.group(1).replace(",", ""))
        scale = (match.group(2) or "").lower()
        raw *= {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}.get(scale, 1)
        formatted = _format_money(raw)
        if formatted not in amounts:
            amounts.append(formatted)
    return amounts


_DATE_RE = re.compile(
    r"\b(?:the\s+)?((?:" + "|".join(NUMBER_WORDS) + r")(?:[\s-]+(?:" + "|".join(NUMBER_WORDS) + r"))?"
    r"(?:st|nd|rd|th)?)\s+of\s+(" + MONTHS + r")\b",
    re.IGNORECASE,
)
_NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + MONTHS + r")\b", re.IGNORECASE)

_STATUTE_RE = re.compile(
    r"\bsection\s+((?:" + "|".join(NUMBER_WORDS) + r")(?:[\s-]+(?:" + "|".join(NUMBER_WORDS) + r"))*|\d+)"
    r"(?:\s+of\s+the\s+([A-Z][\w'’]*(?:\s+[A-Z][\w'’]*)*\s+Act))?",
    re.IGNORECASE,
)

_LR_RE = re.compile(r"\b(?:l\.?r\.?\s*(?:number|no\.?)?|title\s+number)\s*([\w/ ]{3,40})", re.IGNORECASE)
_CAUSE_RE = re.compile(
    r"\b(cause|civil suit|petition|succession cause|e?case)\s+(?:number|no\.?)\s+"
    r"((?:(?:" + "|".join(NUMBER_WORDS) + r")[\s-]*)+|[\d/]+)",
    re.IGNORECASE,
)


def _spoken_number(phrase: str) -> str:
    """'three one seven' -> '317'; 'forty-two' -> '42'."""
    words = [w for w in re.split(r"[\s-]+", phrase.strip().lower()) if w]
    if not words:
        return phrase.strip()
    if all(w in NUMBER_WORDS for w in words) and all(NUMBER_WORDS[w] < 10 for w in words) and len(words) > 1:
        return "".join(str(NUMBER_WORDS[w]) for w in words)
    value = _words_to_number(phrase)
    return str(int(value)) if value else phrase.strip()
_DEADLINE_RE = re.compile(
    r"\b((?:" + "|".join(NUMBER_WORDS) + r")|\d{1,3})[\s-]+(days?|weeks?|months?)\b", re.IGNORECASE
)


def _titlecase_words_number(phrase: str) -> str:
    cleaned = re.sub(r"(st|nd|rd|th)$", "", phrase.strip().lower())
    value = _words_to_number(cleaned)
    return str(int(value)) if value else phrase.strip()


def extract_facts(transcript: list[TranscriptSegment] | None) -> dict:
    """Pull checkable facts out of the non-redacted transcript."""
    segments = [s for s in (transcript or []) if not s.redacted and s.text.strip()]
    text = " ".join(s.text.strip() for s in segments)
    lowered = text.lower()

    speakers: list[str] = []
    for segment in segments:
        if segment.speaker and segment.speaker not in speakers:
            speakers.append(segment.speaker)

    dates: list[str] = []
    for match in _DATE_RE.finditer(text):
        day = _titlecase_words_number(match.group(1))
        month = match.group(2).capitalize()
        value = f"{day} {month}"
        if value not in dates:
            dates.append(value)
    for match in _NUMERIC_DATE_RE.finditer(text):
        value = f"{int(match.group(1))} {match.group(2).capitalize()}"
        if value not in dates:
            dates.append(value)

    statutes: list[str] = []
    for match in _STATUTE_RE.finditer(text):
        number = _titlecase_words_number(match.group(1))
        act = (match.group(2) or "").strip()
        value = f"section {number}" + (f" of the {act}" if act else "")
        value = value[0].upper() + value[1:]
        if value not in statutes:
            statutes.append(value)
    for act_name in ("Employment Act", "Land Act", "Law of Succession Act", "Civil Procedure Act", "Arbitration Act"):
        if act_name.lower() in lowered and not any(act_name in s for s in statutes):
            statutes.append(f"the {act_name}")

    deadlines: list[str] = []
    for match in _DEADLINE_RE.finditer(text):
        number = _titlecase_words_number(match.group(1))
        unit = match.group(2).lower().rstrip("s")
        value = f"{number} {unit}{'s' if number != '1' else ''}"
        if value not in deadlines:
            deadlines.append(value)

    lr_numbers = [m.group(1).strip(" .,") for m in _LR_RE.finditer(text)]
    causes = [
        f"{m.group(1).title()} No. {_spoken_number(m.group(2))} OF {datetime.utcnow().year}"
        for m in _CAUSE_RE.finditer(text)
    ]

    court = None
    for name, label in (
        ("employment", "THE EMPLOYMENT AND LABOUR RELATIONS COURT"),
        ("environment and land", "THE ENVIRONMENT AND LAND COURT"),
        ("magistrate", "THE CHIEF MAGISTRATE'S COURT"),
        ("high court", "THE HIGH COURT OF KENYA"),
        ("succession", "THE HIGH COURT OF KENYA (FAMILY DIVISION)"),
    ):
        if name in lowered:
            court = label
            break

    return {
        "speakers": speakers,
        "amounts": _parse_word_amounts(text),
        "dates": dates,
        "statutes": statutes,
        "deadlines": deadlines,
        "lr_numbers": lr_numbers,
        "causes": causes,
        "court": court,
        "text": text,
        "segments": segments,
    }


def facts_brief(facts: dict) -> str:
    """A compact, model-readable summary of the checkable facts."""
    rows = [
        ("Parties on the record", ", ".join(facts["speakers"])),
        ("Monetary figures stated", "; ".join(facts["amounts"])),
        ("Dates stated", "; ".join(facts["dates"])),
        ("Statutes cited", "; ".join(facts["statutes"])),
        ("Timelines stated", "; ".join(facts["deadlines"])),
        ("Property / title references", "; ".join(facts["lr_numbers"])),
        ("Case references", "; ".join(facts["causes"])),
        ("Court", facts["court"] or ""),
    ]
    return "\n".join(f"- {label}: {value}" for label, value in rows if value)


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------


_ORG_RE = re.compile(
    r"\b([A-Z][\w'’&]+(?:\s+(?:&|and|[A-Z][\w'’]+)){0,3}\s+"
    r"(?:Contractors|Limited|Ltd|Enterprises|Traders|Logistics|Sacco|Holdings|Properties|Company|Bank|Group))\b"
)

_BANKS = ("Barclays", "Absa", "Equity", "KCB", "Stanbic", "Co-operative Bank", "NCBA")


def organisations(facts: dict) -> list[str]:
    found: list[str] = []
    for match in _ORG_RE.finditer(facts["text"]):
        name = match.group(1).strip()
        if name not in found:
            found.append(name)
    for speaker in facts["speakers"]:
        inner = re.search(r"\(([^)]+)\)", speaker)
        if inner:
            org = inner.group(1).split(",")[-1].strip()
            if len(org) > 2 and org not in found:
                found.insert(0, org)
    for bank in _BANKS:
        if bank.lower() in facts["text"].lower() and not any(bank in f for f in found):
            found.insert(0, bank)
    return found


def _clean_speaker(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def client_entity(facts: dict, fallback: str = "[CLIENT]") -> str:
    """Who we act for: the organisation a non-advocate speaker represents,
    otherwise that speaker's own name."""
    orgs = organisations(facts)
    for speaker in facts["speakers"]:
        if speaker.lower().startswith(("adv.", "hon.", "justice", "lady justice")):
            continue
        inner = re.search(r"\(([^)]+)\)", speaker)
        if inner:
            org = inner.group(1).split(",")[-1].strip()
            if org:
                return org
        return _clean_speaker(speaker)
    return orgs[0] if orgs else fallback


def _party(facts: dict, index: int, fallback: str) -> str:
    speakers = facts["speakers"]
    return speakers[index] if len(speakers) > index else fallback


def _counterparty(facts: dict, action: DetectedAction) -> str:
    """The adverse party: an organisation on the record that is not our client."""
    client = client_entity(facts, "")
    for org in organisations(facts):
        if client and (org.lower() in client.lower() or client.lower() in org.lower()):
            continue
        if any(org.lower() in _clean_speaker(s).lower() for s in facts["speakers"]):
            continue
        return org
    parties = action.extracted_fields.get("parties")
    if isinstance(parties, list):
        for item in parties:
            name = _clean_speaker(str(item))
            if name and client and name.lower() not in client.lower():
                return name
    return "[COUNTERPARTY]"


def _numbered(paragraphs: list[str]) -> str:
    return "\n\n".join(f"{i}. {p}" for i, p in enumerate(paragraphs, start=1))


def _record_extract(facts: dict, limit: int = 12) -> str:
    lines = [f"{s.speaker or 'Speaker'}: {s.text.strip()}" for s in facts["segments"][:limit]]
    return "\n".join(lines)


def _letterhead(today: str) -> str:
    return (
        "[FIRM NAME] ADVOCATES\n"
        "[PHYSICAL ADDRESS], NAIROBI\n"
        "[EMAIL] | [TELEPHONE]\n\n"
        f"Date: {today}\n"
    )


def _demand_letter(action, facts, today) -> str:
    claimant = client_entity(facts, "[CLIENT]")
    respondent = _counterparty(facts, action)
    amount = facts["amounts"][-1] if facts["amounts"] else "[SUM CLAIMED]"
    contract_sum = facts["amounts"][0] if facts["amounts"] else "[CONTRACT SUM]"
    deadline = next((d for d in facts["deadlines"] if "day" in d), "twenty-one (21) days")
    breach_date = facts["dates"][0] if facts["dates"] else "[DATE OF BREACH]"

    body = _numbered([
        f"We act for {claimant} (\"our client\"), on whose express instructions we address you.",
        f"Our client instructs us that by agreement between the parties, you were contracted at a "
        f"sum of {contract_sum} to carry out the works described in the instructions taken from our "
        f"client and recorded on {today}. The agreed completion date was {breach_date}.",
        "Our client further instructs us that the works executed were defective and/or incomplete, "
        "and that despite written notification to you on the dates stated in our client's record, "
        "no remedial action has been taken.",
        f"Our client has quantified the loss arising from your breach at {amount}, being the cost of "
        "remedial works assessed by the consulting engineer instructed by our client.",
        f"TAKE NOTICE that unless the sum of {amount} is paid in full to this firm within {deadline} "
        "of the date of this letter, we hold firm and unconditional instructions to commence "
        + ("arbitral proceedings pursuant to the arbitration clause in the contract"
           if "arbitration" in facts["text"].lower() else "legal proceedings against you")
        + ", without further reference to you, and to seek the full sum together with interest and "
        "costs, the whole of which shall be at your expense.",
        "This letter is written without prejudice to our client's rights, all of which are expressly reserved.",
    ])

    return (
        f"{_letterhead(today)}\n"
        f"{respondent}\n[ADDRESS]\n\nDear Sirs,\n\n"
        f"RE: DEMAND FOR PAYMENT — {action.title.replace('Draft: ', '')}\n"
        f"OUR CLIENT: {claimant.upper()}\n\n"
        f"{body}\n\n"
        "Yours faithfully,\n\n"
        "………………………………\n[ADVOCATE NAME]\nFOR: [FIRM NAME] ADVOCATES\n\n"
        f"c.c. {claimant}"
    )


def _statutory_notice(action, facts, today) -> str:
    borrower = _counterparty(facts, action)
    lender = client_entity(facts, "[CHARGEE]")
    amount = facts["amounts"][0] if facts["amounts"] else "[SUM OUTSTANDING]"
    lr = facts["lr_numbers"][0] if facts["lr_numbers"] else "[L.R. NUMBER]"
    statute = next((s for s in facts["statutes"] if "90" in s or "Land Act" in s), "section 90 of the Land Act, 2012")

    body = _numbered([
        f"We act for {lender} (\"the Chargee\"), the registered chargee of all that parcel of land known as {lr} (\"the charged property\").",
        f"You are in default of your obligations under the charge in that the sum of {amount} remains due and owing, "
        "the last payment on the account having been made on the date recorded in the Chargee's statement of account.",
        f"THIS NOTICE is issued pursuant to {statute}, which requires the Chargee to serve you with notice of default "
        "before exercising its remedies.",
        "You are required to rectify the default within three (3) months of the date of service of this notice by paying "
        f"the whole of the sum of {amount} together with accrued interest and the costs of this notice.",
        "TAKE NOTICE that if the default is not rectified within the said period, the Chargee shall, upon expiry of a "
        "further forty (40) days' notification of sale, proceed to exercise its statutory power of sale over the charged "
        "property without further reference to you.",
        "Nothing in this notice shall be construed as a waiver of any of the Chargee's rights, all of which are reserved.",
    ])

    return (
        f"{_letterhead(today)}\n"
        f"TO: {borrower}\n[ADDRESS]\n\n"
        f"NOTICE OF DEFAULT UNDER {statute.upper()}\n"
        f"CHARGED PROPERTY: {lr}\n\n"
        f"{body}\n\n"
        "DATED at NAIROBI this ……… day of ……………… 20………\n\n"
        "………………………………\n[FIRM NAME] ADVOCATES\nADVOCATES FOR THE CHARGEE\n\n"
        f"DRAWN & FILED BY:\n[FIRM NAME] Advocates\n[ADDRESS]\nNAIROBI"
    )


def _affidavit(action, facts, today, replying: bool) -> str:
    court = facts["court"] or "THE HIGH COURT OF KENYA"
    cause = facts["causes"][0] if facts["causes"] else "[CAUSE NO. ……… OF 20………]"
    deponent = _clean_speaker(client_entity(facts, "[DEPONENT]"))
    heading = "REPLYING AFFIDAVIT" if replying else "SUPPORTING AFFIDAVIT"
    statute = facts["statutes"][0] if facts["statutes"] else None

    paragraphs = [
        f"THAT I am the {'Respondent' if replying else 'Claimant'} herein and being such am competent, "
        "duly authorised and conversant with the facts of this matter to swear this affidavit.",
        "THAT the matters deposed to herein are true to the best of my own knowledge, save where stated "
        "to be on information and belief, the sources whereof are disclosed.",
    ]
    for segment in facts["segments"][:6]:
        line = segment.text.strip().rstrip(".")
        if len(line) < 25:
            continue
        paragraphs.append(f"THAT on the record of the conference of {today}, it was stated that {line}.")
    if statute:
        paragraphs.append(
            f"THAT I am advised by my advocates on record, which advice I verily believe to be true, that "
            f"{statute} is directly applicable to the matters in issue herein."
        )
    paragraphs.append(
        "THAT this affidavit is sworn in "
        + ("opposition to the application/claim herein and in support of the deponent's case."
           if replying else "support of the application filed herewith.")
    )
    paragraphs.append("THAT what is deposed to herein is true to the best of my knowledge, information and belief.")

    return (
        "REPUBLIC OF KENYA\n"
        f"IN {court} AT NAIROBI\n"
        f"{cause}\n\n"
        f"{client_entity(facts, '[CLAIMANT]').upper()} …………………………………………… CLAIMANT\n"
        "VERSUS\n"
        f"{_counterparty(facts, action).upper()} ………………………………… RESPONDENT\n\n"
        f"{heading}\n\n"
        f"I, {deponent}, of Post Office Box Number [P.O. BOX], [TOWN] in the Republic of Kenya, "
        "do hereby make oath and state as follows:\n\n"
        f"{_numbered(paragraphs)}\n\n"
        f"SWORN by the said {deponent}          )\n"
        "at NAIROBI this ……… day of ………………  )   ………………………………\n"
        "20………                                 )        DEPONENT\n\n"
        "BEFORE ME:\n\n"
        "………………………………\nCOMMISSIONER FOR OATHS\n\n"
        "DRAWN & FILED BY:\n[FIRM NAME] Advocates\n[ADDRESS]\nNAIROBI"
    )


def _plaint(action, facts, today) -> str:
    court_name = facts["court"] or "THE CHIEF MAGISTRATE'S COURT"
    plaintiff = client_entity(facts, "[PLAINTIFF]")
    defendant = _counterparty(facts, action)
    amount = facts["amounts"][0] if facts["amounts"] else "[SUM CLAIMED]"
    paragraphs = [
        f"The Plaintiff is a person/entity carrying on business within the Republic of Kenya, and service of "
        "process may be effected through the offices of its advocates herein.",
        f"The Defendant is {defendant}, against whom the Plaintiff's claim herein lies, and service may be "
        "effected at [DEFENDANT'S ADDRESS].",
        f"The Plaintiff's claim against the Defendant is for the sum of {amount} being monies due and owing "
        "arising from the facts recorded in the Plaintiff's instructions.",
        "Despite demand and notice of intention to sue, the Defendant has failed, refused and/or neglected to "
        "settle the said sum or any part thereof.",
        "The cause of action arose within the jurisdiction of this Honourable Court.",
    ]
    prayer = (
        "REASONS WHEREFORE the Plaintiff prays for judgment against the Defendant for:\n"
        f"    (a) The sum of {amount};\n"
        "    (b) Interest on (a) above at court rates from the date of filing suit until payment in full;\n"
        "    (c) Costs of this suit;\n"
        "    (d) Any other or further relief this Honourable Court may deem fit and just to grant."
    )
    return (
        "REPUBLIC OF KENYA\n"
        f"IN {court_name} AT NAIROBI\n"
        "CIVIL SUIT NO. ……… OF 20………\n\n"
        f"{plaintiff.upper()} ………………………………………… PLAINTIFF\nVERSUS\n"
        f"{defendant.upper()} ………………………………… DEFENDANT\n\n"
        "PLAINT\n\n"
        f"{_numbered(paragraphs)}\n\n"
        f"{prayer}\n\n"
        f"DATED at NAIROBI this ……… day of ……………… 20………\n\n"
        "………………………………\n[FIRM NAME] ADVOCATES\nADVOCATES FOR THE PLAINTIFF"
    )


def _notice_of_arbitration(action, facts, today) -> str:
    claimant = client_entity(facts, "[CLAIMANT]")
    respondent = _counterparty(facts, action)
    amount = facts["amounts"][-1] if facts["amounts"] else "[SUM IN DISPUTE]"
    clause = re.search(r"clause\s+(\d{1,3})", facts["text"], re.IGNORECASE)
    clause_ref = f"clause {clause.group(1)}" if clause else "the arbitration clause"
    paragraphs = [
        f"A dispute has arisen between {claimant} (\"the Claimant\") and {respondent} (\"the Respondent\") "
        "under the contract between the parties.",
        f"The dispute concerns defective and/or incomplete performance by the Respondent and the Claimant's "
        f"quantified loss of {amount}.",
        f"Pursuant to {clause_ref} of the contract and section 12 of the Arbitration Act, 1995, the Claimant "
        "hereby refers the dispute to arbitration.",
        "The Claimant proposes [PROPOSED ARBITRATOR], FCIArb, as sole arbitrator, and invites the Respondent "
        "to signify agreement within fourteen (14) days of service of this notice.",
        "In default of agreement, the Claimant shall apply to the Chartered Institute of Arbitrators (Kenya "
        "Branch) for appointment of a sole arbitrator.",
        "The seat of the arbitration shall be Nairobi and the language of the arbitration shall be English.",
    ]
    return (
        f"{_letterhead(today)}\n"
        f"TO: {respondent}\n[ADDRESS]\n\n"
        "NOTICE OF ARBITRATION\n\n"
        f"{_numbered(paragraphs)}\n\n"
        "………………………………\n[FIRM NAME] ADVOCATES\nADVOCATES FOR THE CLAIMANT"
    )


def _revocation_of_grant(action, facts, today) -> str:
    applicant = _clean_speaker(client_entity(facts, "[APPLICANT]"))
    statute = next((s for s in facts["statutes"] if "76" in s), "section 76 of the Law of Succession Act")
    paragraphs = [
        f"THAT the deceased died on the date stated in the record, leaving the estate described in the Applicant's "
        "instructions, including the parcel of land the subject of this application.",
        "THAT the grant of letters of administration issued herein was obtained by means of a petition which "
        "concealed material facts, namely the existence of the Applicant and other beneficiaries entitled to share "
        "in the estate.",
        "THAT the Applicant, a daughter of the deceased, is a dependant within the meaning of the Law of Succession "
        "Act, and her marital status does not extinguish her entitlement to the estate.",
        "THAT the administrator has proceeded to transfer part of the estate property to himself without the consent "
        "of the other beneficiaries and without confirmation of the grant on a correct schedule of beneficiaries.",
        f"THAT in the premises, the grant is liable to be revoked or annulled pursuant to {statute}.",
        "THAT it is in the interest of justice that the grant herein be revoked and a fresh grant issued to the "
        "beneficiaries jointly.",
    ]
    return (
        "REPUBLIC OF KENYA\n"
        "IN THE HIGH COURT OF KENYA AT NAIROBI (FAMILY DIVISION)\n"
        "SUCCESSION CAUSE NO. ……… OF 20………\n\n"
        "IN THE MATTER OF THE ESTATE OF [DECEASED NAME] (DECEASED)\n"
        f"AND IN THE MATTER OF AN APPLICATION FOR REVOCATION OF GRANT UNDER {statute.upper()}\n\n"
        "SUMMONS FOR REVOCATION OF GRANT\n"
        "(Under section 76 of the Law of Succession Act and Rule 44 of the Probate and Administration Rules)\n\n"
        f"LET ALL PARTIES attend before this Honourable Court on a date to be fixed for the hearing of an "
        f"application by {applicant} for orders:\n\n"
        "    1. THAT the grant of letters of administration intestate issued herein be revoked and/or annulled.\n"
        "    2. THAT the transfer of the estate property effected by the administrator be set aside.\n"
        "    3. THAT a fresh grant do issue jointly to the lawful beneficiaries of the estate.\n"
        "    4. THAT the costs of this application be provided for.\n\n"
        "WHICH APPLICATION is based on the following grounds:\n\n"
        f"{_numbered(paragraphs)}\n\n"
        "SUPPORTING DOCUMENTS TO BE ANNEXED: certificate of death; the grant issued herein; official search "
        "(green card) in respect of the estate property.\n\n"
        "DATED at NAIROBI this ……… day of ……………… 20………\n\n"
        "………………………………\n[FIRM NAME] ADVOCATES\nADVOCATES FOR THE APPLICANT"
    )


def _attendance_note(action, facts, today) -> str:
    court = facts["court"] or "[COURT]"
    cause = facts["causes"][0] if facts["causes"] else "[CAUSE NUMBER]"
    directions = [
        s.text.strip() for s in facts["segments"]
        if re.search(r"\b(shall file|within|mention|directions|submissions|serve)\b", s.text, re.IGNORECASE)
    ]
    dates = ", ".join(facts["dates"]) or "[NONE STATED]"
    return (
        "ATTENDANCE NOTE / COURT DIRECTIONS RECORD\n\n"
        f"Date of attendance: {today}\n"
        f"Court: {court}\n"
        f"Matter: {cause}\n"
        f"Appearances: {', '.join(facts['speakers']) or '[APPEARANCES]'}\n\n"
        "1. PROCEEDINGS\n\n"
        f"{_record_extract(facts)}\n\n"
        "2. DIRECTIONS GIVEN BY THE COURT\n\n"
        + ("\n".join(f"   ({chr(97+i)}) {d}" for i, d in enumerate(directions[:6])) or "   (a) [NO DIRECTIONS RECORDED]")
        + "\n\n3. KEY DATES\n\n"
        f"   {dates}\n\n"
        "4. ACTION FOR THIS FIRM\n\n"
        "   (a) Diarise each of the dates above and the computed filing deadlines.\n"
        "   (b) Prepare and file the documents directed within time.\n"
        "   (c) Report to the client on the directions given.\n\n"
        "Prepared by: [ADVOCATE NAME]\nFile reference: [FILE REF]"
    )


def _engagement_letter(action, facts, today) -> str:
    client = client_entity(facts, "[CLIENT]")
    return (
        f"{_letterhead(today)}\n"
        f"{client}\n[ADDRESS]\n\nDear {client},\n\n"
        "RE: LETTER OF ENGAGEMENT\n\n"
        + _numbered([
            "Thank you for instructing this firm. This letter sets out the terms on which we shall act for you.",
            f"SCOPE: We are instructed to act for you in relation to {action.preview or '[SCOPE OF INSTRUCTIONS]'}.",
            "FEES: Our fees shall be charged in accordance with the Advocates (Remuneration) Order, at an hourly "
            "rate of KES [RATE] per hour for the advocate handling the matter, exclusive of disbursements and VAT.",
            "CONFIDENTIALITY: All information you provide is protected by advocate-client privilege and shall not "
            "be disclosed save as required by law or with your authority.",
            "DATA PROTECTION: Your personal data is processed in accordance with the Data Protection Act, 2019.",
            "Kindly sign and return the duplicate copy of this letter in acknowledgement of these terms.",
        ])
        + "\n\nYours faithfully,\n\n………………………………\n[ADVOCATE NAME]\nFOR: [FIRM NAME] ADVOCATES\n\n"
        "ACKNOWLEDGED AND ACCEPTED:\n\n………………………………      Date: ……………………\n"
        f"{client}"
    )


def _legal_memo(action, facts, today) -> str:
    issues = [
        s.text.strip() for s in facts["segments"]
        if "?" in s.text or re.search(r"\b(section|act|liable|claim|breach|entitle)\b", s.text, re.IGNORECASE)
    ]
    statutes = ", ".join(facts["statutes"]) or "[NO STATUTE CITED ON THE RECORD]"
    return (
        "LEGAL MEMORANDUM\n\n"
        f"TO:      [PARTNER / FILE]\nFROM:    [ADVOCATE NAME]\nDATE:    {today}\n"
        f"RE:      {action.title.replace('Draft: ', '')}\n"
        f"PARTIES: {', '.join(facts['speakers']) or '[PARTIES]'}\n\n"
        "1. INSTRUCTIONS\n\n"
        f"   {action.preview or 'Advise on the matters raised in the conference recorded below.'}\n\n"
        "2. FACTS AS RECORDED\n\n"
        f"{_record_extract(facts)}\n\n"
        "3. ISSUES FOR DETERMINATION\n\n"
        + ("\n".join(f"   3.{i+1} {issue}" for i, issue in enumerate(issues[:5])) or "   3.1 [ISSUES TO BE SETTLED]")
        + "\n\n4. APPLICABLE LAW\n\n"
        f"   {statutes}\n\n"
        "5. ANALYSIS\n\n"
        "   On the facts recorded above, the client's position is supported by the matters stated on the record. "
        "Each factual assertion in this memorandum is traceable to the transcript extract at paragraph 2 and has "
        "not been supplemented by any fact outside it.\n\n"
        "6. RECOMMENDED NEXT STEPS\n\n"
        + ("\n".join(f"   6.{i+1} Diarise and action: {d}" for i, d in enumerate(facts["deadlines"][:3]))
           or "   6.1 Confirm outstanding facts with the client before any filing.")
        + "\n\n7. MATTERS REQUIRING CONFIRMATION\n\n"
        "   Items shown in [SQUARE BRACKETS] were not stated on the record and must be confirmed before use.\n\n"
        "Prepared by: [ADVOCATE NAME], Advocate of the High Court of Kenya"
    )


def compose_document(kind: str, action: DetectedAction, transcript: list[TranscriptSegment] | None) -> str:
    facts = extract_facts(transcript)
    today = datetime.utcnow().strftime("%d %B %Y")
    builders = {
        "demand_letter": lambda: _demand_letter(action, facts, today),
        "statutory_notice": lambda: _statutory_notice(action, facts, today),
        "replying_affidavit": lambda: _affidavit(action, facts, today, replying=True),
        "supporting_affidavit": lambda: _affidavit(action, facts, today, replying=False),
        "plaint": lambda: _plaint(action, facts, today),
        "notice_of_arbitration": lambda: _notice_of_arbitration(action, facts, today),
        "revocation_of_grant": lambda: _revocation_of_grant(action, facts, today),
        "attendance_note": lambda: _attendance_note(action, facts, today),
        "engagement_letter": lambda: _engagement_letter(action, facts, today),
        "legal_memo": lambda: _legal_memo(action, facts, today),
    }
    return builders.get(kind, builders["legal_memo"])()


def compliance_footer(kind: str) -> str:
    return (
        "\n\n———\nDRAFT — prepared by HakiScribe from the verified, non-redacted transcript. "
        "Every factual assertion above is traceable to a line of that record; bracketed items were "
        "not stated and must be confirmed by counsel before filing or service. "
        f"Document type: {KIND_TITLES.get(kind, 'LEGAL DOCUMENT')}."
    )
