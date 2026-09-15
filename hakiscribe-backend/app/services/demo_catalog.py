"""Seed matters and transcripts for the HakiScribe demo desk.

Kept free of storage imports so ``seed_demo.py`` can reuse the same catalog
against a remote API without booting the local store.
"""

from __future__ import annotations

from typing import Any

SHOWCASE_TITLE = "Client meeting — Wanjiru Holdings, defective works at Kilimani site"
SAHARA_DEMO_TITLE = "Sahara multilingual demo — Milimani court hearing (EN–SW code-switch)"

# All Sahara-seeded demos (primary first). ensure_sahara_demo materializes every title.
SAHARA_DEMO_TITLES: list[str] = [
    SAHARA_DEMO_TITLE,
    "Sahara refine — Wanjiru Holdings site memo (EN–SW)",
    "Sahara refine — Otieno ELRC chambers note (EN–SW)",
    "Sahara refine — Coastal Sacco Nyali recovery call (EN–SW)",
    "Sahara refine — Githunguri succession intake (EN–SW)",
    "Sahara refine — Karanja Westlands distress briefing (EN–Sheng)",
]


def _seg(
    speaker: str,
    text: str,
    start_s: float,
    dur_s: float = 6,
    *,
    provider: str | None = None,
    source_extra: dict[str, Any] | None = None,
) -> dict:
    segment: dict[str, Any] = {
        "speaker": speaker,
        "text": text,
        "start_ms": int(start_s * 1000),
        "end_ms": int((start_s + dur_s) * 1000),
        "confidence": 0.94,
    }
    if provider:
        raw = {"provider": provider}
        if source_extra:
            raw.update(source_extra)
        segment["source_raw"] = raw
    return segment


def _sahara(
    speaker: str,
    text: str,
    start_s: float,
    dur_s: float = 6,
    *,
    court: bool = False,
) -> dict:
    extra: dict[str, Any] = {"mode": "file_category_legal"}
    if court:
        extra["get_legal_court_hearing"] = True
    return _seg(speaker, text, start_s, dur_s, provider="sahara", source_extra=extra)


MATTERS: list[dict[str, str]] = [
    {"client_name": "Wanjiru Holdings Ltd", "matter_name": "Wanjiru Holdings v. Sarova Contractors — construction defect"},
    {"client_name": "Achieng' Otieno", "matter_name": "Otieno — employment termination claim"},
    {"client_name": "Mombasa Coastal Sacco", "matter_name": "Coastal Sacco — loan recovery portfolio"},
    {"client_name": "Barclays", "matter_name": "Barclays vs. Apex Logistics"},
    {"client_name": "Apex Logistics (EA) Limited", "matter_name": "Barclays vs. Apex Logistics — facility default"},
    {"client_name": "Githunguri Family Estate", "matter_name": "Estate of the late Njoroge Kamau — succession"},
    {"client_name": "Karanja & Sons Ltd", "matter_name": "Karanja & Sons v. Riverside Properties — irregular distress"},
    {
        "client_name": "Kamau Enterprises Ltd",
        "matter_name": "Wanjiru Holdings Ltd v. Kamau Enterprises Ltd — lease arrears (Milimani CS 204/2026)",
    },
]

SESSIONS: list[dict[str, Any]] = [
    {
        "title": SHOWCASE_TITLE,
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Wanjiru Holdings Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "James Wanjiru"},
        "flags": [
            {"at_ms": 192000, "label": "Payment withheld — key fact"},
            {"at_ms": 356000, "label": "Deadline for demand letter"},
        ],
        "segments": [
            _seg("Speaker 1", "Thanks for coming in, James. Before we start — this conversation is privileged. Take me through what happened at the Kilimani site.", 0, 9),
            _seg("Speaker 2", "Sarova Contractors were meant to complete the slab works by the fifteenth of June. By July the slab had visible cracking on the second floor.", 9, 11),
            _seg("Speaker 1", "Did you raise it with them in writing?", 20, 4),
            _seg("Speaker 2", "Yes, twice. Email on the second of July, then a WhatsApp on the eighteenth. They said they would send an engineer, hakuna kitu ilifanyika.", 24, 12),
            _seg("Speaker 1", "And the contract sum? What has been paid so far?", 36, 5),
            _seg("Speaker 2", "Contract was eighteen million shillings. We have paid twelve point six million. We withheld the balance after the cracking.", 41, 11),
            _seg("Speaker 2", "The structural engineer, Eng. Mutiso, says remedial works will cost about four point two million.", 52, 9),
            _seg("Speaker 1", "Good. That gives us a quantified loss. I want to send a formal demand letter to Sarova Contractors before we consider arbitration under clause 41.", 61, 13),
            _seg("Speaker 2", "How long do they get?", 74, 3),
            _seg("Speaker 1", "Twenty-one days. If they don't respond we file a notice of arbitration. Let's also diarise a follow-up meeting on the third of October at ten in the morning.", 77, 14),
            _seg("Speaker 2", "That works. Also, please keep the bit about my partner's tax position out of anything you write.", 91, 8),
            _seg("Speaker 1", "Noted — that stays off the record. I'll get the demand letter to you for review by Friday.", 99, 8),
        ],
        "redact_indexes": [10],
        "generate": True,
    },
    {
        "title": "Sahara refine — Wanjiru Holdings site memo (EN–SW)",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Wanjiru Holdings Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki"},
        "flags": [{"at_ms": 28000, "label": "Remedial cost — KES 4.2M"}],
        "segments": [
            _sahara("Speaker 1", "Voice memo kwa file ya Wanjiru Holdings. After the Kilimani site visit, Eng. Mutiso confirms remedial works at about four point two million shillings.", 0, 12),
            _sahara("Speaker 1", "Sarova bado haijalipa — they have not answered the demand. Tafadhali draft a follow-up letter giving seven more days before we issue the arbitration notice under clause forty-one.", 12, 14),
            _sahara("Speaker 1", "Diarise a call with James Wanjiru on Friday at nine. Keep the partner tax discussion off the record — that stays privileged.", 26, 11),
            _sahara("Speaker 1", "Hii memo inafaa kuingia Action Tray as draft_document and calendar_event.", 37, 7),
        ],
        "redact_indexes": [],
        "generate": True,
    },
    {
        "title": "Court proceeding — Employment & Labour Relations Court, Otieno termination",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Achieng' Otieno",
        "speakers": {"Speaker 1": "Hon. Justice Mwangi", "Speaker 2": "Adv. Naomi Kariuki", "Speaker 3": "Adv. Peter Ochieng"},
        "flags": [{"at_ms": 145000, "label": "Court directions — filing dates"}],
        "segments": [
            _seg("Speaker 1", "Cause number forty-two of this year, Achieng' Otieno versus Bidii Logistics Limited. Appearances please.", 0, 9),
            _seg("Speaker 2", "Kariuki for the claimant, my lord.", 9, 4),
            _seg("Speaker 3", "Ochieng' for the respondent.", 13, 3),
            _seg("Speaker 2", "My lord, the claimant was summarily dismissed on the ninth of March without a show cause letter and without a hearing, contrary to section forty-one of the Employment Act.", 16, 14),
            _seg("Speaker 3", "My lord, the respondent's position is that the claimant abandoned duty for eleven consecutive days.", 30, 9),
            _seg("Speaker 1", "Counsel, has the respondent filed a replying affidavit?", 39, 5),
            _seg("Speaker 3", "Not yet, my lord. We seek fourteen days.", 44, 4),
            _seg("Speaker 1", "The respondent shall file and serve a replying affidavit within fourteen days. The claimant may file a supplementary affidavit within seven days thereafter.", 48, 13),
            _seg("Speaker 1", "Mention on the twenty-eighth of October at nine o'clock for further directions. Highlighting of submissions thereafter.", 61, 10),
            _seg("Speaker 2", "Much obliged, my lord.", 71, 3),
        ],
        "redact_indexes": [],
        "generate": True,
    },
    {
        "title": "Sahara refine — Otieno ELRC chambers note (EN–SW)",
        "source": "mic",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Achieng' Otieno",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Achieng' Otieno"},
        "flags": [{"at_ms": 42000, "label": "Mention — 28 October"}],
        "segments": [
            _sahara(
                "Speaker 1",
                "Achieng', mahakama imeweka mention on the twenty-eighth of October. The respondent must file a replying affidavit within fourteen days.",
                0,
                12,
                court=True,
            ),
            _sahara("Speaker 2", "Je, hiyo ina-mean nini kwa case yangu? Will I get my salary for February and March?", 12, 9),
            _sahara("Speaker 1", "It means we keep pressure on Bidii Logistics. We will also prepare a supplementary affidavit if they raise the abandonment story again. Nataka ulete payslips and the dismissal letter by Friday.", 21, 14),
            _sahara("Speaker 2", "Sawa. Also, my sister helped me with school fees — that bit is private, usiiandike kwenye letter.", 35, 9),
            _sahara("Speaker 1", "Noted, that stays off the record. I will draft a client update letter and diarise the mention.", 44, 9),
        ],
        "redact_indexes": [3],
        "generate": True,
    },
    {
        "title": "Client call — Mombasa Coastal Sacco, defaulted loan recovery strategy",
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Mombasa Coastal Sacco",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Fatuma Said (CEO, Coastal Sacco)"},
        "flags": [{"at_ms": 88000, "label": "Statutory notice timeline"}],
        "segments": [
            _seg("Speaker 1", "Fatuma, you mentioned three accounts in default. Give me the worst one first.", 0, 7),
            _seg("Speaker 2", "Mwakio Enterprises. Four point eight million outstanding, last payment was in November. Security is a title in Nyali, LR number Mombasa slash Block Twelve slash three four one.", 7, 15),
            _seg("Speaker 1", "Have you issued a statutory notice under section ninety of the Land Act?", 22, 6),
            _seg("Speaker 2", "Hapana, not yet. We only sent internal reminder letters.", 28, 5),
            _seg("Speaker 1", "Then we start there — a three months' statutory notice, then the forty days' notification before sale. I'll prepare the section ninety notice this week.", 33, 13),
            _seg("Speaker 2", "And the other two? Kadzo Traders is about nine hundred thousand, unsecured.", 46, 7),
            _seg("Speaker 1", "For unsecured, a demand then a plaint in the Magistrate's Court. Let's open a recovery matter for the Sacco portfolio so everything sits in one file.", 53, 13),
            _seg("Speaker 2", "Please do. Can we meet on the twentieth of September at two p.m. to review all three?", 66, 8),
            _seg("Speaker 1", "Twentieth at two works. I'll circulate a status note before then.", 74, 7),
        ],
        "redact_indexes": [],
        "generate": False,
    },
    {
        "title": "Sahara refine — Coastal Sacco Nyali recovery call (EN–SW)",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Mombasa Coastal Sacco",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Fatuma Said (CEO, Coastal Sacco)"},
        "flags": [{"at_ms": 36000, "label": "Section 90 notice — Mwakio"}],
        "segments": [
            _sahara("Speaker 2", "Naomi, Mwakio bado hajalipa. Four point eight million is outstanding. Title iko Nyali, LR Mombasa Block Twelve slash three four one.", 0, 12),
            _sahara("Speaker 1", "Tutaanza na section ninety statutory notice this week. After three months, the forty days' notification before sale. Hapana shortcuts.", 12, 12),
            _sahara("Speaker 2", "Na Kadzo Traders? Nine hundred thousand, unsecured — tunaweza file plaint Mombasa Magistrate Court?", 24, 9),
            _sahara("Speaker 1", "Yes. I will open one recovery matter for the portfolio, draft the Mwakio notice, and calendar our review on the twentieth at two p.m.", 33, 12),
            _sahara("Speaker 2", "Asante. Please keep the board's internal provisioning figure off anything you send outside.", 45, 8),
            _sahara("Speaker 1", "Understood — that stays privileged. Status note before the meeting.", 53, 7),
        ],
        "redact_indexes": [4],
        "generate": True,
    },
    {
        "title": "Intake — new client, land succession dispute in Kiambu",
        "source": "mic",
        "language_hint": "code-switch",
        "client_name": "Githunguri Family Estate",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Grace Njeri"},
        "flags": [{"at_ms": 52000, "label": "Limitation concern"}],
        "segments": [
            _seg("Speaker 1", "Grace, tell me about the land and who is currently on the title.", 0, 6),
            _seg("Speaker 2", "My late father's parcel in Kiambu, Githunguri. He died in twenty-nineteen. My brother obtained letters of administration and transferred two acres to himself.", 6, 15),
            _seg("Speaker 1", "Were you listed as a beneficiary in the petition?", 21, 5),
            _seg("Speaker 2", "No. He said I was married so sitakuwa na haki. My mother and two sisters were also left out.", 26, 9),
            _seg("Speaker 1", "That's not the law. Under the Law of Succession Act a married daughter remains a beneficiary. We can apply to revoke the grant under section seventy-six.", 35, 14),
            _seg("Speaker 2", "Is it too late? It's been a while.", 49, 4),
            _seg("Speaker 1", "Revocation isn't strictly time-barred where the grant was obtained by concealment, but we should move quickly. Bring the death certificate, the grant, and the green card search.", 53, 15),
            _seg("Speaker 2", "I'll get them next week.", 68, 3),
        ],
        "redact_indexes": [],
        "generate": False,
    },
    {
        "title": "Sahara refine — Githunguri succession intake (EN–SW)",
        "source": "mic",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Githunguri Family Estate",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Grace Njeri"},
        "flags": [{"at_ms": 50000, "label": "Revocation under s.76"}],
        "segments": [
            _sahara("Speaker 2", "Dada, brother alichukua grant bila majina yetu. He transferred two acres in Githunguri to himself after baba died in twenty-nineteen.", 0, 13),
            _sahara("Speaker 1", "Under the Law of Succession Act, a married daughter remains a beneficiary. Sitakuwa na haki is not the law. We can apply to revoke the grant under section seventy-six.", 13, 14),
            _sahara("Speaker 2", "Mama and my two sisters were also left out. Is it too late?", 27, 7),
            _sahara("Speaker 1", "Revocation is available where the grant was obtained by concealment, but we must move quickly. Lete death certificate, the grant, and the green card search next week.", 34, 14),
            _sahara("Speaker 2", "Sawa. One thing — the family meeting about our sister abroad is private, usiiweke kwenye affidavit.", 48, 9),
            _sahara("Speaker 1", "That stays off the record. I will open a succession matter and draft a first advice letter.", 57, 9),
        ],
        "redact_indexes": [4],
        "generate": True,
    },
    {
        "title": "Case conference — Barclays vs. Apex Logistics, facility default and charge enforcement",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Barclays",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Susan Mbugua (Head of Recoveries, Barclays)", "Speaker 3": "Adv. Brian Kiptoo"},
        "flags": [
            {"at_ms": 63000, "label": "Statutory notice not yet issued"},
            {"at_ms": 121000, "label": "Ruling date — Milimani"},
        ],
        "segments": [
            _seg("Speaker 2", "Naomi, the Apex Logistics facility is now firmly in default. The outstanding is one hundred and forty million shillings as at the end of last month.", 0, 12),
            _seg("Speaker 1", "And the security held by the bank?", 12, 4),
            _seg("Speaker 2", "A legal charge over the Industrial Area godown, L.R. number two zero nine slash one one four three, plus a debenture over the fleet.", 16, 12),
            _seg("Speaker 1", "Has the bank issued a statutory notice under section ninety of the Land Act?", 28, 7),
            _seg("Speaker 2", "Hapana, not yet. Credit wanted a restructure first, but Apex have missed the last three instalments.", 35, 9),
            _seg("Speaker 1", "Then the sequence is a section ninety notice, then the forty days' notification before sale. We should also file a plaint in the Milimani Commercial Court for the unsecured portion.", 44, 15),
            _seg("Speaker 3", "Apex have already written threatening an injunction over the godown.", 59, 7),
            _seg("Speaker 1", "Expected. We prepare a replying affidavit in advance so we are not caught flat-footed if they move ex parte.", 66, 10),
            _seg("Speaker 2", "The bank also wants a formal demand letter on record before any of that.", 76, 7),
            _seg("Speaker 1", "Agreed — demand letter first, fourteen days, then the statutory notice. Ruling on the pending application is on the twelfth of October at eleven.", 83, 13),
            _seg("Speaker 2", "One more thing — keep the internal provisioning figure out of anything filed.", 96, 7),
            _seg("Speaker 1", "Understood, that stays off the record. I will circulate drafts by Wednesday.", 103, 8),
        ],
        "redact_indexes": [10],
        "generate": True,
    },
    {
        "title": "Client meeting — Karanja & Sons, commercial lease dispute at Westlands",
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Peter Karanja (Director, Karanja & Sons Ltd)"},
        "flags": [{"at_ms": 71000, "label": "Distress for rent — key exposure"}],
        "segments": [
            _seg("Speaker 1", "Peter, take me through what the landlord has done at the Westlands premises.", 0, 7),
            _seg("Speaker 2", "Riverside Properties Limited levied distress last Thursday. They locked our warehouse and took stock worth about six million shillings.", 7, 13),
            _seg("Speaker 1", "Are you in arrears?", 20, 3),
            _seg("Speaker 2", "Three months, about two point four million. But the lease says they must give thirty days' notice before any distress.", 23, 11),
            _seg("Speaker 1", "Did they serve that notice?", 34, 4),
            _seg("Speaker 2", "Nothing. We only got a phone call from the caretaker on the morning of the lock-out.", 38, 8),
            _seg("Speaker 1", "Then the distress is irregular. We can move the Business Premises Rent Tribunal for a reference and an interim order restoring possession.", 46, 13),
            _seg("Speaker 2", "How fast can we move?", 59, 3),
            _seg("Speaker 1", "We file the reference this week and seek an interim order within seven days. I will also write a demand letter to Riverside Properties for the value of the goods taken.", 62, 15),
            _seg("Speaker 2", "Please do. Can we meet on the twenty-fifth of September at eleven to sign the affidavit?", 77, 9),
            _seg("Speaker 1", "Twenty-fifth at eleven works. Bring the lease, the rent schedule and photographs of the lock-out.", 86, 10),
        ],
        "redact_indexes": [],
        "generate": True,
    },
    {
        "title": "Sahara refine — Karanja Westlands distress briefing (EN–Sheng)",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Peter Karanja (Director, Karanja & Sons Ltd)"},
        "flags": [{"at_ms": 40000, "label": "Irregular distress — BPRT"}],
        "segments": [
            _sahara("Speaker 2", "Bro, landlord alilock warehouse jana. Stock worth about six million. Hapana notice — only a call from the caretaker.", 0, 11),
            _sahara("Speaker 1", "Lease ina-require thirty days' notice before distress. Without it, the levy is irregular. Tutaenda Business Premises Rent Tribunal for a reference and interim restoration.", 11, 14),
            _sahara("Speaker 2", "Arrears ni three months, two point four million — but process ilikuwa wrong. How fast can we move?", 25, 9),
            _sahara("Speaker 1", "We file this week and seek an interim order within seven days. I will also demand Riverside for the value of goods taken. Meeting twenty-fifth at eleven to sign the affidavit.", 34, 14),
            _sahara("Speaker 2", "Poa. Keep the conversation about the side cash sale off paper — that one is sensitive.", 48, 8),
            _sahara("Speaker 1", "Privileged. Bring the lease, rent schedule, and photos of the lock-out.", 56, 8),
        ],
        "redact_indexes": [4],
        "generate": True,
    },
    {
        "title": "Court proceeding — Milimani Commercial Court, Riverside Properties injunction application",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {"Speaker 1": "Hon. Lady Justice Wambui", "Speaker 2": "Adv. Naomi Kariuki", "Speaker 3": "Adv. Brian Kiptoo"},
        "flags": [{"at_ms": 96000, "label": "Interim orders granted"}],
        "segments": [
            _seg("Speaker 1", "Civil suit number three one seven of this year, Karanja and Sons Limited versus Riverside Properties Limited. Appearances.", 0, 10),
            _seg("Speaker 2", "Kariuki for the applicant, my lady.", 10, 4),
            _seg("Speaker 3", "Kiptoo for the respondent.", 14, 3),
            _seg("Speaker 2", "My lady, the respondent levied distress on the eleventh of September without the thirty days' notice required under the lease and without a court process.", 17, 14),
            _seg("Speaker 3", "My lady, the applicant is in arrears of two point four million shillings and the respondent acted within its contractual right of re-entry.", 31, 11),
            _seg("Speaker 1", "Counsel, was any notice served in writing before the distress?", 42, 6),
            _seg("Speaker 3", "Not in writing, my lady.", 48, 3),
            _seg("Speaker 1", "The court grants an interim order restraining the respondent from selling or disposing of the attached goods pending the hearing of the application inter partes.", 51, 14),
            _seg("Speaker 1", "The respondent shall file a replying affidavit within fourteen days. The applicant may file a supplementary affidavit within seven days thereafter.", 65, 13),
            _seg("Speaker 1", "Mention on the twelfth of October at eleven o'clock for directions on the main suit.", 78, 9),
            _seg("Speaker 2", "Much obliged, my lady.", 87, 3),
        ],
        "redact_indexes": [],
        "generate": True,
    },
    {
        "title": SAHARA_DEMO_TITLE,
        "source": "mic",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Kamau Enterprises Ltd",
        "speakers": {
            "Speaker 1": "Hon. Lady Justice Wambui",
            "Speaker 2": "Adv. Naomi Kariuki",
            "Speaker 3": "Adv. Peter Ochieng",
        },
        "flags": [
            {"at_ms": 48000, "label": "Arrears quantified — KES 450,000"},
            {"at_ms": 98000, "label": "Hearing date fixed"},
        ],
        "segments": [
            _sahara(
                "Speaker 1",
                "COURT HEARING RECORD — Milimani Commercial Court. Civil Suit number two zero four of twenty twenty-six, Wanjiru Holdings Limited versus Kamau Enterprises Limited. Appearances please.",
                0,
                12,
                court=True,
            ),
            _sahara(
                "Speaker 2",
                "Kariuki for the plaintiff, my lady. Mheshimiwa, the defendant owes KES four hundred and fifty thousand under the lease agreement signed March twenty twenty-four.",
                12,
                14,
                court=True,
            ),
            _sahara(
                "Speaker 3",
                "Ochieng for the defendant. My lady, hatutaki kucheleweshwa tena, but we dispute the quantum and seek time to file a replying affidavit.",
                26,
                12,
                court=True,
            ),
            _sahara("Speaker 1", "Counsel for the plaintiff, have you issued a formal demand?", 38, 5, court=True),
            _sahara(
                "Speaker 2",
                "Yes, my lady. Demand letter dated the twelfth of August. Hapana response within the fourteen days granted. We request a hearing date within thirty days na amri ya mahakama on interim rent deposit.",
                43,
                16,
                court=True,
            ),
            _sahara(
                "Speaker 1",
                "The court notes the arrears at KES four hundred and fifty thousand. The defendant shall file and serve a replying affidavit within fourteen days. Mention on the fourteenth of April twenty twenty-six at ten o'clock in the forenoon.",
                59,
                16,
                court=True,
            ),
            _sahara(
                "Speaker 2",
                "Much obliged, my lady. We will also prepare a draft demand update for the client file and diarise the mention.",
                75,
                10,
                court=True,
            ),
            _sahara(
                "Speaker 3",
                "Off the record, my instructing client mentioned a side settlement discussion that must not enter the court record.",
                85,
                9,
                court=True,
            ),
            _sahara(
                "Speaker 1",
                "That exchange stays off the record. Hii ni amri ya mahakama, na inafuata. Court rises.",
                94,
                8,
                court=True,
            ),
        ],
        "redact_indexes": [7],
        "generate": True,
    },
]
