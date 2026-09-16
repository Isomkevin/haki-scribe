"""Seed matters and transcripts for the HakiScribe demo desk.

Kept free of storage imports so ``seed_demo.py`` can reuse the same catalog
against a remote API without booting the local store.
"""

from __future__ import annotations

from typing import Any

SHOWCASE_TITLE = "Client meeting — Wanjiru Holdings, defective works at Kilimani site"
# Primary multilingual hearing demo (seeded as Sahara legal refine; title blends with library).
SAHARA_DEMO_TITLE = "Court proceeding — Milimani Commercial Court, Wanjiru Holdings lease arrears"

# Multilingual / code-switch seeds mixed through existing matters (primary first).
SAHARA_DEMO_TITLES: list[str] = [
    SAHARA_DEMO_TITLE,
    "Voice memo — Wanjiru Holdings, Kilimani remedial works follow-up",
    "Client briefing — Otieno, ELRC directions after mention",
    "Client call — Coastal Sacco, Nyali statutory notice plan",
    "Follow-up intake — Githunguri succession, revocation advice",
    "Site briefing — Karanja & Sons, Westlands distress after lock-out",
    "Client intake — Bello Trading, Kano warehouse lease dispute",
    "Client call — Adeyemi & Co, Lagos employment notice review",
    "Mention notes — Dlamini, Johannesburg eviction defence",
]


def _seg(
    speaker: str,
    text: str,
    start_s: float,
    dur_s: float = 6,
    *,
    provider: str | None = None,
    source_extra: dict[str, Any] | None = None,
    confidence: float = 0.94,
) -> dict:
    segment: dict[str, Any] = {
        "speaker": speaker,
        "text": text,
        "start_ms": int(start_s * 1000),
        "end_ms": int((start_s + dur_s) * 1000),
        "confidence": confidence,
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
    confidence: float = 0.94,
) -> dict:
    extra: dict[str, Any] = {"mode": "file_category_legal"}
    if court:
        extra["get_legal_court_hearing"] = True
    return _seg(
        speaker,
        text,
        start_s,
        dur_s,
        provider="sahara",
        source_extra=extra,
        confidence=confidence,
    )


def _timed(
    lines: list[tuple[str, str]],
    *,
    pace: float = 2.15,
    gap_s: float = 0.35,
    builder=_seg,
    builder_kwargs: dict[str, Any] | None = None,
) -> list[dict]:
    """Build consecutive segments with durations from word count (~130 wpm)."""
    kwargs = dict(builder_kwargs or {})
    segs: list[dict] = []
    t = 0.0
    for i, (speaker, text) in enumerate(lines):
        words = max(1, len(text.split()))
        dur = max(2.8, round(words / pace, 1))
        if i:
            t += gap_s
        # Slight confidence jitter — short turns usually clearer.
        conf = 0.96 if words <= 10 else 0.93 if words <= 28 else 0.90
        segs.append(builder(speaker, text, t, dur, confidence=conf, **kwargs))
        t += dur
    return segs


def _flag_near(segments: list[dict], index: int, label: str) -> dict[str, Any]:
    idx = max(0, min(index, len(segments) - 1))
    return {"at_ms": segments[idx]["start_ms"], "label": label}


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
    {"client_name": "Bello Trading Ltd", "matter_name": "Bello Trading v. Northern Logistics — warehouse lease (Kano)"},
    {"client_name": "Adeyemi & Co", "matter_name": "Adeyemi — wrongful dismissal claim (Lagos)"},
    {"client_name": "Thandi Dlamini", "matter_name": "Dlamini — residential eviction defence (Johannesburg)"},
]


def _wanjiru_showcase() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Thanks for coming in, James. Before we start — this conversation is privileged and confidential. Take me through what happened at the Kilimani site from the beginning.",
            ),
            (
                "Speaker 2",
                "Sarova Contractors were meant to complete the slab works by the fifteenth of June. By early July the slab had visible cracking on the second floor, and water was seeping near the stair core.",
            ),
            ("Speaker 1", "Mm. Did you raise it with them in writing?"),
            (
                "Speaker 2",
                "Yes, twice. Formal email on the second of July, then a WhatsApp follow-up on the eighteenth. They said they would send an engineer — hakuna kitu ilifanyika. No visit, no written plan.",
            ),
            ("Speaker 1", "And the contract sum? What has been paid so far, and what have you withheld?"),
            (
                "Speaker 2",
                "Contract was eighteen million shillings. We have paid twelve point six million against certified works. We withheld the balance after the cracking showed up.",
            ),
            (
                "Speaker 2",
                "The structural engineer, Eng. Mutiso, inspected last week. He says remedial works will cost about four point two million, and he put that in a signed report.",
            ),
            ("Speaker 1", "Good — that gives us a quantified loss. Do you have photos and the payment schedule ready to attach?"),
            (
                "Speaker 2",
                "Photos yes. Payment schedule I can send this afternoon together with Mutiso's PDF. There is also a site diary from our clerk if that helps.",
            ),
            (
                "Speaker 1",
                "Attach all three. I want to send a formal demand letter to Sarova Contractors before we consider arbitration under clause forty-one of the contract.",
            ),
            ("Speaker 2", "How long do they get to respond?"),
            (
                "Speaker 1",
                "Twenty-one days from service. If they don't respond substantively, we file a notice of arbitration. Let's also diarise a follow-up meeting on the third of October at ten in the morning.",
            ),
            (
                "Speaker 2",
                "That works. Also, please keep the bit about my partner's tax position out of anything you write — that stays between us.",
            ),
            (
                "Speaker 1",
                "Noted — that stays off the record. I'll get the demand letter to you for review by Friday, then we serve once you approve.",
            ),
            (
                "Speaker 2",
                "Asante, Naomi. I will send Mutiso's report, the payment schedule, and the photos this afternoon.",
            ),
            (
                "Speaker 1",
                "Perfect. Once I have those, the letter goes out. Call me tomorrow if anything else comes up on site.",
            ),
        ]
    )
    return {
        "title": SHOWCASE_TITLE,
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Wanjiru Holdings Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "James Wanjiru"},
        "flags": [
            _flag_near(segments, 5, "Payment withheld — key fact"),
            _flag_near(segments, 11, "Deadline for demand letter"),
        ],
        "segments": segments,
        "redact_indexes": [12],
        "generate": True,
    }


def _wanjiru_voice_memo() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Voice memo for the Wanjiru Holdings file. Leo nilitembelea Kilimani site with Eng. Mutiso. He confirms remedial works at about four point two million shillings — cracked slab on the second floor, same pattern as July.",
            ),
            (
                "Speaker 1",
                "Sarova bado haijalipa, and they have not answered our demand of the twelfth of August. Fourteen days zimeisha without a substantive reply — only a vague email saying they are still assessing.",
            ),
            (
                "Speaker 1",
                "Tafadhali draft a follow-up letter giving them seven more days. If they still ignore us, we issue the arbitration notice under clause forty-one of the contract.",
            ),
            (
                "Speaker 1",
                "Attach Mutiso's report and the payment schedule showing twelve point six million already paid against the eighteen million contract sum. Make clear the balance remains withheld for cause.",
            ),
            (
                "Speaker 1",
                "Also note that water ingress near the stair core is now visible in the latest photos — that strengthens urgency on remedial works.",
            ),
            (
                "Speaker 1",
                "Diarise a call with James Wanjiru on Friday at nine o'clock. I want him to approve the follow-up letter before it goes out.",
            ),
            (
                "Speaker 1",
                "Keep the partner tax discussion completely off this memo and off any letter — that stays privileged. End of memo.",
            ),
        ],
        builder=_sahara,
        pace=2.05,
    )
    return {
        "title": "Voice memo — Wanjiru Holdings, Kilimani remedial works follow-up",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Wanjiru Holdings Ltd",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki"},
        "flags": [
            _flag_near(segments, 0, "Remedial cost — KES 4.2M"),
            _flag_near(segments, 2, "Seven-day follow-up before arbitration"),
        ],
        "segments": segments,
        "redact_indexes": [6],
        "generate": True,
    }


def _otieno_court() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Cause number forty-two of this year, Achieng' Otieno versus Bidii Logistics Limited. Appearances please.",
            ),
            ("Speaker 2", "Kariuki for the claimant, my lord."),
            ("Speaker 3", "Ochieng' for the respondent."),
            (
                "Speaker 2",
                "My lord, the claimant was summarily dismissed on the ninth of March without a show cause letter and without a hearing, contrary to section forty-one of the Employment Act.",
            ),
            (
                "Speaker 2",
                "She seeks reinstatement, or in the alternative compensation for unfair termination, unpaid February and March salary, and a certificate of service.",
            ),
            (
                "Speaker 3",
                "My lord, the respondent's position is that the claimant abandoned duty for eleven consecutive days. We dispute that procedure was not followed and we will put medical leave in issue.",
            ),
            ("Speaker 1", "Counsel, has the respondent filed a replying affidavit?"),
            ("Speaker 3", "Not yet, my lord. We seek fourteen days to file and serve."),
            (
                "Speaker 2",
                "My lord, we have no objection to fourteen days, provided the claimant may reply thereafter and the mention is not pushed past October.",
            ),
            (
                "Speaker 1",
                "The respondent shall file and serve a replying affidavit within fourteen days. The claimant may file a supplementary affidavit within seven days thereafter.",
            ),
            (
                "Speaker 1",
                "Mention on the twenty-eighth of October at nine o'clock for further directions. Highlighting of submissions thereafter. Costs in the cause.",
            ),
            ("Speaker 2", "Much obliged, my lord."),
            ("Speaker 3", "As the court pleases."),
            ("Speaker 1", "That is the order of the court. Next matter."),
        ],
        pace=2.0,
        gap_s=0.5,
    )
    return {
        "title": "Court proceeding — Employment & Labour Relations Court, Otieno termination",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Achieng' Otieno",
        "speakers": {
            "Speaker 1": "Hon. Justice Mwangi",
            "Speaker 2": "Adv. Naomi Kariuki",
            "Speaker 3": "Adv. Peter Ochieng",
        },
        "flags": [
            _flag_near(segments, 3, "Summary dismissal — no show cause"),
            _flag_near(segments, 10, "Court directions — filing dates"),
        ],
        "segments": segments,
        "redact_indexes": [],
        "generate": True,
    }


def _otieno_briefing() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Achieng', asante kwa kuja. Mahakama imeweka mention on the twenty-eighth of October at nine. The respondent, Bidii Logistics, must file a replying affidavit within fourteen days.",
            ),
            (
                "Speaker 2",
                "Je, hiyo ina-mean nini kwa case yangu? Will I get my salary for February and March, and can I go back to work?",
            ),
            (
                "Speaker 1",
                "It means we keep pressure on them. We asked for reinstatement or compensation for unfair dismissal. Nataka ulete payslips, the dismissal letter, and any WhatsApp with your supervisor by Friday.",
            ),
            (
                "Speaker 2",
                "Sawa, nitawaleta. They said I abandoned duty, but I had sent medical notes to HR and copied my line manager. Do I need more witnesses?",
            ),
            (
                "Speaker 1",
                "If they raise abandonment again, we file a supplementary affidavit with those notes and a colleague who can confirm you reported sick. Tutafanya follow-up call after they serve their papers.",
            ),
            (
                "Speaker 2",
                "Okay. One more thing — my sister helped me with school fees when I was unpaid. That bit is private, usiiandike kwenye letter to the court or to Bidii.",
            ),
            (
                "Speaker 1",
                "Noted, that stays off the record. I will draft a short client update letter summarising today's directions and diarise the twenty-eighth mention.",
            ),
            ("Speaker 2", "Asante sana, advocate. Niko ready for Friday — I can drop the documents at chambers."),
            (
                "Speaker 1",
                "Good. Bring originals and leave scans if you can. We will be ready when Bidii files, and I will call you the day after they serve.",
            ),
        ],
        builder=_sahara,
        builder_kwargs={"court": True},
        pace=2.1,
    )
    return {
        "title": "Client briefing — Otieno, ELRC directions after mention",
        "source": "mic",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Achieng' Otieno",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Achieng' Otieno"},
        "flags": [
            _flag_near(segments, 0, "Mention — 28 October"),
            _flag_near(segments, 2, "Payslips and dismissal letter by Friday"),
        ],
        "segments": segments,
        "redact_indexes": [5],
        "generate": True,
    }


def _coastal_strategy() -> dict[str, Any]:
    segments = _timed(
        [
            ("Speaker 1", "Fatuma, you mentioned three accounts in default. Give me the worst one first."),
            (
                "Speaker 2",
                "Mwakio Enterprises. Four point eight million outstanding, last payment was in November. Security is a title in Nyali, L.R. number Mombasa Block Twelve slash three four one.",
            ),
            ("Speaker 1", "Have you issued a statutory notice under section ninety of the Land Act?"),
            (
                "Speaker 2",
                "Hapana, not yet. We only sent internal reminder letters and one board chase-up. Credit wanted to wait for a restructuring proposal that never came.",
            ),
            (
                "Speaker 1",
                "Then we start there — a three months' statutory notice, then the forty days' notification before sale. I'll prepare the section ninety notice this week.",
            ),
            (
                "Speaker 2",
                "And the other two? Kadzo Traders is about nine hundred thousand, unsecured. Hassan Supply is one point two million with a personal guarantee from the director.",
            ),
            (
                "Speaker 1",
                "For unsecured, a demand then a plaint in the Magistrate's Court. For Hassan we enforce the guarantee in parallel. Let's open one recovery matter for the Sacco portfolio so everything sits in one file.",
            ),
            (
                "Speaker 2",
                "Please do. Can we meet on the twentieth of September at two p.m. to review all three, with drafts on the table?",
            ),
            (
                "Speaker 1",
                "Twentieth at two works. I'll circulate a status note before then, with draft notices attached for Mwakio, Kadzo, and Hassan.",
            ),
            (
                "Speaker 2",
                "One caution — keep the board's internal provisioning numbers out of anything external. Those figures are for the board pack only.",
            ),
            (
                "Speaker 1",
                "Understood. That stays privileged. I will only use the contractual outstanding figures and the security particulars in the notices.",
            ),
            ("Speaker 2", "Asante, Naomi. Send me the drafts for Mwakio first — that is the one burning."),
            ("Speaker 1", "You will have them by Wednesday. If Mwakio pays anything before then, call me immediately."),
        ]
    )
    return {
        "title": "Client call — Mombasa Coastal Sacco, defaulted loan recovery strategy",
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Mombasa Coastal Sacco",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Fatuma Said (CEO, Coastal Sacco)"},
        "flags": [
            _flag_near(segments, 4, "Statutory notice timeline"),
            _flag_near(segments, 7, "Review meeting — 20 September"),
        ],
        "segments": segments,
        "redact_indexes": [9],
        "generate": True,
    }


def _coastal_nyali() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 2",
                "Naomi, asante kwa kupiga. Mwakio bado hajalipa. Four point eight million is outstanding since November. Title iko Nyali, L.R. Mombasa Block Twelve slash three four one.",
            ),
            (
                "Speaker 1",
                "Tutaanza na section ninety statutory notice this week. After three months, the forty days' notification before sale. Hapana shortcuts — Land Act process lazima ifuatwe.",
            ),
            (
                "Speaker 2",
                "Na Kadzo Traders? Nine hundred thousand, unsecured — tunaweza file plaint Mombasa Magistrate Court? Hassan Supply also, one point two million with a personal guarantee.",
            ),
            (
                "Speaker 1",
                "Yes. Demand then plaint for Kadzo. For Hassan we sue on the guarantee as well. I will open one recovery matter for the portfolio so all three sit together.",
            ),
            (
                "Speaker 2",
                "Board wants a short written status before our review. Can you include expected timelines for each file?",
            ),
            (
                "Speaker 1",
                "I will draft the Mwakio notice, circulate a short status note with timelines, and calendar our review on the twentieth of September at two p.m.",
            ),
            (
                "Speaker 2",
                "Poa. Please keep the board's internal provisioning figure off anything you send outside — that one is sensitive.",
            ),
            (
                "Speaker 1",
                "Understood — that stays privileged. Notices will only show contractual outstanding and the security particulars.",
            ),
            ("Speaker 2", "Asante. Send Mwakio draft first, then Kadzo and Hassan demands."),
            (
                "Speaker 1",
                "By Wednesday. If Mwakio pays anything before then, niambie immediately so we pause the notice.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Client call — Coastal Sacco, Nyali statutory notice plan",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Mombasa Coastal Sacco",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Fatuma Said (CEO, Coastal Sacco)"},
        "flags": [
            _flag_near(segments, 1, "Section 90 notice — Mwakio"),
            _flag_near(segments, 5, "Portfolio review — 20 September 2 p.m."),
        ],
        "segments": segments,
        "redact_indexes": [6],
        "generate": True,
    }


def _githunguri_intake() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Grace, thank you for coming in. This conversation is privileged. Tell me about the land and who is currently on the title.",
            ),
            (
                "Speaker 2",
                "My late father's parcel in Kiambu, Githunguri — about four acres in total. He died in twenty-nineteen. My brother obtained letters of administration and transferred two acres to himself.",
            ),
            ("Speaker 1", "Were you listed as a beneficiary in the petition for the grant?"),
            (
                "Speaker 2",
                "No. He said I was married so sitakuwa na haki. My mother and two sisters were also left out. None of us were served with the petition or the gazette notice.",
            ),
            (
                "Speaker 1",
                "That's not the law. Under the Law of Succession Act a married daughter remains a beneficiary. We can apply to revoke the grant under section seventy-six for concealment of material facts.",
            ),
            ("Speaker 2", "Is it too late? It's been a while since the transfer, and he has started fencing."),
            (
                "Speaker 1",
                "Revocation isn't strictly time-barred where the grant was obtained by concealment, but we should move quickly before further dealings or a sale to a third party.",
            ),
            (
                "Speaker 1",
                "Bring the death certificate, the grant, the green card search, and any message where he said married daughters have no share. Those support the concealment ground.",
            ),
            (
                "Speaker 2",
                "I'll get them next week. There is also a family meeting planned about our sister who lives abroad — that discussion should stay private.",
            ),
            (
                "Speaker 1",
                "Understood, that stays off the record. I will open a succession matter, draft a first advice letter, and we meet again once documents are in.",
            ),
            ("Speaker 2", "Asante. I will call when I have the green card from Kiambu lands."),
            (
                "Speaker 1",
                "Do that. Meanwhile avoid any further family transfers or signing on that title. We protect the estate first.",
            ),
        ]
    )
    return {
        "title": "Intake — new client, land succession dispute in Kiambu",
        "source": "mic",
        "language_hint": "code-switch",
        "client_name": "Githunguri Family Estate",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Grace Njeri"},
        "flags": [
            _flag_near(segments, 4, "Revocation under section 76"),
            _flag_near(segments, 6, "Limitation concern"),
        ],
        "segments": segments,
        "redact_indexes": [8],
        "generate": True,
    }


def _githunguri_followup() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 2",
                "Dada Naomi, nimerudi as you asked. Brother alichukua grant bila majina yetu. He transferred two acres in Githunguri to himself after baba died in twenty-nineteen.",
            ),
            (
                "Speaker 1",
                "Under the Law of Succession Act, a married daughter remains a beneficiary. Sitakuwa na haki is not the law. We apply to revoke the grant under section seventy-six for concealment.",
            ),
            (
                "Speaker 2",
                "Mama and my two sisters were also left out. We were never served with the petition. Is it too late to reverse the transfer?",
            ),
            (
                "Speaker 1",
                "Revocation is available where the grant was obtained by concealment, but we must move quickly before more dealings. Once the grant falls, the transfer can be challenged.",
            ),
            (
                "Speaker 1",
                "Lete death certificate, the grant, the green card search, and any SMS or letter where he said married daughters have no share. Next week is fine if you start collecting this week.",
            ),
            (
                "Speaker 2",
                "Sawa. One thing — the family meeting about our sister abroad and how we support her is private. Usiiweke kwenye affidavit au advice letter.",
            ),
            (
                "Speaker 1",
                "That stays off the record. I will open a succession matter today and draft a first advice letter outlining the revocation path and the documents we need.",
            ),
            (
                "Speaker 2",
                "Asante sana. Nitakupigia Friday once I have the green card from Kiambu lands. I already booked the search.",
            ),
            (
                "Speaker 1",
                "Perfect. Until then, hakuna further signing on that title. We protect the estate first, then we talk distribution.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Follow-up intake — Githunguri succession, revocation advice",
        "source": "mic",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Githunguri Family Estate",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Grace Njeri"},
        "flags": [
            _flag_near(segments, 1, "Revocation under s.76"),
            _flag_near(segments, 4, "Documents due next week"),
        ],
        "segments": segments,
        "redact_indexes": [5],
        "generate": True,
    }


def _barclays_apex() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 2",
                "Naomi, the Apex Logistics facility is now firmly in default. The outstanding is one hundred and forty million shillings as at the end of last month, interest still accruing.",
            ),
            ("Speaker 1", "And the security held by the bank?"),
            (
                "Speaker 2",
                "A legal charge over the Industrial Area godown, L.R. number two zero nine slash one one four three, plus a debenture over the fleet and receivables.",
            ),
            ("Speaker 1", "Has the bank issued a statutory notice under section ninety of the Land Act?"),
            (
                "Speaker 2",
                "Hapana, not yet. Credit wanted a restructure first, but Apex have missed the last three instalments and the restructure talks collapsed last Friday.",
            ),
            (
                "Speaker 1",
                "Then the sequence is a formal demand, then section ninety notice, then the forty days' notification before sale. We should also file a plaint in the Milimani Commercial Court for the unsecured portion.",
            ),
            (
                "Speaker 3",
                "Apex have already written threatening an injunction over the godown if we move to sell. They claim the valuation is outdated.",
            ),
            (
                "Speaker 1",
                "Expected. We prepare a replying affidavit in advance so we are not caught flat-footed if they move ex parte. Brian, please start that draft this week and pull the latest valuation.",
            ),
            ("Speaker 2", "The bank also wants a formal demand letter on record before any of that."),
            (
                "Speaker 1",
                "Agreed — demand letter first, fourteen days to remedy, then the statutory notice. Ruling on the pending application in Milimani is on the twelfth of October at eleven.",
            ),
            (
                "Speaker 2",
                "One more thing — keep the internal provisioning figure out of anything filed or sent to Apex. That number stays inside the bank.",
            ),
            (
                "Speaker 1",
                "Understood, that stays off the record. I will circulate the demand draft and a short litigation plan by Wednesday.",
            ),
            ("Speaker 3", "I will diarise the twelfth and start the replying affidavit skeleton today."),
            ("Speaker 2", "Good. Let's reconvene after the demand goes out — preferably the same week."),
        ],
        pace=2.1,
    )
    return {
        "title": "Case conference — Barclays vs. Apex Logistics, facility default and charge enforcement",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Barclays",
        "speakers": {
            "Speaker 1": "Adv. Naomi Kariuki",
            "Speaker 2": "Susan Mbugua (Head of Recoveries, Barclays)",
            "Speaker 3": "Adv. Brian Kiptoo",
        },
        "flags": [
            _flag_near(segments, 4, "Statutory notice not yet issued"),
            _flag_near(segments, 9, "Ruling date — Milimani 12 October"),
        ],
        "segments": segments,
        "redact_indexes": [10],
        "generate": True,
    }


def _karanja_meeting() -> dict[str, Any]:
    segments = _timed(
        [
            ("Speaker 1", "Peter, take me through what the landlord has done at the Westlands premises — start from last Thursday."),
            (
                "Speaker 2",
                "Riverside Properties Limited levied distress last Thursday. They locked our warehouse and took stock worth about six million shillings, including two perishable lines.",
            ),
            ("Speaker 1", "Are you in arrears, and for how long?"),
            (
                "Speaker 2",
                "Three months, about two point four million. But the lease says they must give thirty days' notice before any distress. Hapana notice ilitolewa — nothing in writing.",
            ),
            ("Speaker 1", "Did they serve that notice in writing, or only by phone?"),
            (
                "Speaker 2",
                "Nothing in writing. We only got a phone call from the caretaker on the morning of the lock-out. Inventory was taken without our representative present.",
            ),
            (
                "Speaker 1",
                "Then the distress is irregular. We can move the Business Premises Rent Tribunal for a reference and an interim order restoring possession, and restrain sale of the goods.",
            ),
            ("Speaker 2", "How fast can we move? Stock is perishable on some lines and we have staff locked out."),
            (
                "Speaker 1",
                "We file the reference this week and seek an interim order within seven days. I will also write a demand letter to Riverside for the value of the goods taken and the unlawful lock-out.",
            ),
            (
                "Speaker 2",
                "Please do. Can we meet on the twenty-fifth of September at eleven to sign the supporting affidavit?",
            ),
            (
                "Speaker 1",
                "Twenty-fifth at eleven works. Bring the lease, the rent schedule, photographs of the lock-out, and a stock list with values.",
            ),
            (
                "Speaker 2",
                "There was also a side cash sale conversation with a neighbour — keep that off any paper we file. It is sensitive for the business.",
            ),
            (
                "Speaker 1",
                "Privileged. It will not appear in the reference or the demand. I will send you a draft affidavit by Monday for review.",
            ),
        ]
    )
    return {
        "title": "Client meeting — Karanja & Sons, commercial lease dispute at Westlands",
        "source": "omi",
        "language_hint": "code-switch",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {
            "Speaker 1": "Adv. Naomi Kariuki",
            "Speaker 2": "Peter Karanja (Director, Karanja & Sons Ltd)",
        },
        "flags": [
            _flag_near(segments, 6, "Distress for rent — key exposure"),
            _flag_near(segments, 9, "Affidavit signing — 25 September"),
        ],
        "segments": segments,
        "redact_indexes": [11],
        "generate": True,
    }


def _karanja_site() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 2",
                "Naomi, niko site. Landlord alilock warehouse jana asubuhi. Stock worth about six million. Hapana written notice — only a call from the caretaker, then padlocks.",
            ),
            (
                "Speaker 1",
                "Lease ina-require thirty days' notice before distress. Without it, the levy is irregular. Tutaenda Business Premises Rent Tribunal for a reference and interim restoration.",
            ),
            (
                "Speaker 2",
                "Arrears ni three months, two point four million — tuna-admit that, but process ilikuwa wrong. Inventory was done without us. How fast can we move?",
            ),
            (
                "Speaker 1",
                "We file this week and seek an interim order within seven days restraining sale and restoring access. I will also demand Riverside for the value of goods taken and the lock-out loss.",
            ),
            (
                "Speaker 1",
                "Meeting twenty-fifth of September at eleven to sign the supporting affidavit. Lete lease, rent schedule, photos, and the stock valuation.",
            ),
            (
                "Speaker 2",
                "Poa. Keep the conversation about the side cash sale with the neighbour off paper — that one is sensitive for the business.",
            ),
            (
                "Speaker 1",
                "Privileged. It will not go in the tribunal papers. I will draft the reference and demand and send both before the signing meeting.",
            ),
            (
                "Speaker 2",
                "Asante. Nitakuwa pale twenty-fifth. Staff wako nje for now — we need that interim order before the perishable stock goes bad.",
            ),
            (
                "Speaker 1",
                "Understood. File goes in this week. Sit tight and do not attempt re-entry without the order.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Site briefing — Karanja & Sons, Westlands distress after lock-out",
        "source": "omi",
        "language_hint": "multilingual",
        "detected_language": "code-switch",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {
            "Speaker 1": "Adv. Naomi Kariuki",
            "Speaker 2": "Peter Karanja (Director, Karanja & Sons Ltd)",
        },
        "flags": [
            _flag_near(segments, 1, "Irregular distress — BPRT"),
            _flag_near(segments, 3, "Interim order within seven days"),
        ],
        "segments": segments,
        "redact_indexes": [5],
        "generate": True,
    }


def _riverside_court() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Civil suit number three one seven of this year, Karanja and Sons Limited versus Riverside Properties Limited. Appearances.",
            ),
            ("Speaker 2", "Kariuki for the applicant, my lady."),
            ("Speaker 3", "Kiptoo for the respondent."),
            (
                "Speaker 2",
                "My lady, the respondent levied distress on the eleventh of September without the thirty days' notice required under the lease and without a court process. Stock valued at about six million was removed.",
            ),
            (
                "Speaker 2",
                "We seek interim orders restraining sale or disposal of the attached goods and restoring the applicant to possession pending inter partes hearing.",
            ),
            (
                "Speaker 3",
                "My lady, the applicant is in arrears of two point four million shillings and the respondent acted within its contractual right of re-entry. Any delay prejudices the landlord.",
            ),
            ("Speaker 1", "Counsel for the respondent, was any notice served in writing before the distress?"),
            ("Speaker 3", "Not in writing, my lady. There was a telephone communication with the caretaker."),
            (
                "Speaker 1",
                "The court grants an interim order restraining the respondent from selling or disposing of the attached goods pending the hearing of the application inter partes. Possession of the premises is restored to the applicant on terms that rent arrears continue to accrue.",
            ),
            (
                "Speaker 1",
                "The respondent shall file a replying affidavit within fourteen days. The applicant may file a supplementary affidavit within seven days thereafter.",
            ),
            (
                "Speaker 1",
                "Mention on the twelfth of October at eleven o'clock for directions on the main suit. Costs in the cause.",
            ),
            ("Speaker 2", "Much obliged, my lady."),
            ("Speaker 3", "As the court pleases."),
            ("Speaker 1", "That is the order. Court rises for a short break."),
        ],
        pace=2.0,
        gap_s=0.5,
    )
    return {
        "title": "Court proceeding — Milimani Commercial Court, Riverside Properties injunction application",
        "source": "mic",
        "language_hint": "en",
        "client_name": "Karanja & Sons Ltd",
        "speakers": {
            "Speaker 1": "Hon. Lady Justice Wambui",
            "Speaker 2": "Adv. Naomi Kariuki",
            "Speaker 3": "Adv. Brian Kiptoo",
        },
        "flags": [
            _flag_near(segments, 8, "Interim orders granted"),
            _flag_near(segments, 10, "Mention — 12 October"),
        ],
        "segments": segments,
        "redact_indexes": [],
        "generate": True,
    }


def _sahara_milimani() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Civil Suit number two zero four of twenty twenty-six, Wanjiru Holdings Limited versus Kamau Enterprises Limited, Milimani Commercial Court. Appearances please.",
            ),
            ("Speaker 2", "Kariuki for the plaintiff, my lady."),
            ("Speaker 3", "Ochieng for the defendant, my lady."),
            (
                "Speaker 2",
                "Mheshimiwa, the claim is for lease arrears of KES four hundred and fifty thousand under the lease agreement signed in March twenty twenty-four for the Industrial Area unit.",
            ),
            (
                "Speaker 2",
                "Demand letter dated the twelfth of August was served. Hapana response within the fourteen days granted. We request a hearing within thirty days and an interim order for deposit of ongoing rent.",
            ),
            (
                "Speaker 3",
                "My lady, hatutaki kucheleweshwa tena, but we dispute the quantum. Part of the alleged arrears relates to service charge that was never particularised. We seek fourteen days to file a replying affidavit.",
            ),
            (
                "Speaker 1",
                "Counsel for the plaintiff, is the four hundred and fifty thousand limited to rent, or does it include service charge?",
            ),
            (
                "Speaker 2",
                "Primarily rent, my lady. We will particularise service charge in a supplementary affidavit if the court so directs.",
            ),
            (
                "Speaker 1",
                "The court notes the arrears claimed at KES four hundred and fifty thousand. The defendant shall file and serve a replying affidavit within fourteen days. The plaintiff may file a supplementary affidavit within seven days thereafter.",
            ),
            (
                "Speaker 1",
                "Mention on the fourteenth of April twenty twenty-six at ten o'clock in the forenoon for directions and fixing of a hearing date. Pending that mention, the defendant shall continue paying the contractual monthly rent into court.",
            ),
            (
                "Speaker 2",
                "Much obliged, my lady. We will diarise the mention and update the client file.",
            ),
            (
                "Speaker 3",
                "As the court pleases. My lady, may we briefly address a scheduling matter off the record regarding a without-prejudice settlement discussion?",
            ),
            (
                "Speaker 1",
                "That exchange stays off the record. Hii ni amri ya mahakama as delivered. Court rises.",
            ),
        ],
        builder=_sahara,
        builder_kwargs={"court": True},
        pace=2.0,
        gap_s=0.5,
    )
    return {
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
            _flag_near(segments, 3, "Arrears quantified — KES 450,000"),
            _flag_near(segments, 9, "Hearing date fixed — 14 April 2026"),
        ],
        "segments": segments,
        "redact_indexes": [11],
        "generate": True,
    }


def _bello_kano() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Sannu da zuwa, Alhaji. Before we begin — this conversation is privileged. Tell me what happened with the Kano warehouse lease.",
            ),
            (
                "Speaker 2",
                "Nagode. Northern Logistics locked the gate on the third of September. They claim we owe eight point four million naira in arrears — gaskiya we dispute three months of service charge that was never billed properly.",
            ),
            ("Speaker 1", "Did they serve a written notice of re-entry before they padlocked the premises?"),
            (
                "Speaker 2",
                "Only a WhatsApp message from their estate manager. No formal letter, no inventory taken with our representative. Staff are safe, but our Abuja consignment is stuck inside.",
            ),
            (
                "Speaker 1",
                "Without proper notice, the lock-out is vulnerable. We will send a fourteen-day demand for restoration of possession and particularisation of the arrears, then move for an interim injunction in the High Court of Kano State if they refuse.",
            ),
            (
                "Speaker 2",
                "Mun so possession first — restore access, then we can negotiate the disputed months. I can pay the undisputed rent into escrow while we argue service charge.",
            ),
            (
                "Speaker 1",
                "That helps. Bring the lease, the payment schedule, photos of the lock-out, and the WhatsApp thread. Draft demand goes out by Friday.",
            ),
            (
                "Speaker 2",
                "One thing — keep the tax discussion with my partner about the side import invoices off this file. That one is sensitive.",
            ),
            (
                "Speaker 1",
                "Understood — that stays privileged. I will diarise a follow-up for next Tuesday at ten after you have sent the documents.",
            ),
            ("Speaker 2", "Nagode sosai. I will email everything this afternoon."),
            (
                "Speaker 1",
                "Good. Do not attempt to force the gate open. We proceed on paper first, then court if they ignore the demand.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Client intake — Bello Trading, Kano warehouse lease dispute",
        "source": "mic",
        "language_hint": "en-ha",
        "detected_language": "multilingual",
        "client_name": "Bello Trading Ltd",
        "speakers": {"Speaker 1": "Adv. Aisha Mohammed", "Speaker 2": "Alhaji Musa Bello"},
        "flags": [
            _flag_near(segments, 1, "Arrears claimed — NGN 8.4M"),
            _flag_near(segments, 4, "Fourteen-day demand before suit"),
        ],
        "segments": segments,
        "redact_indexes": [7],
        "generate": True,
    }


def _adeyemi_lagos() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Ẹ káàbọ̀, Tunde. This call is privileged. Jọ̀wọ́, walk me through the termination letter from your employer.",
            ),
            (
                "Speaker 2",
                "They terminated me on the twelfth without three months' notice in the contract. Salary arrears of two months dey, plus unpaid leave. I need a demand letter before we file at the National Industrial Court.",
            ),
            ("Speaker 1", "Was there a disciplinary hearing or a query before the letter?"),
            (
                "Speaker 2",
                "Nothing. HR just sent the letter by email. My line manager said performance, but no appraisal was shared. Wetin we fit claim exactly?",
            ),
            (
                "Speaker 1",
                "We quantify three months' notice pay, the two months' salary arrears, accrued leave, and damages for unfair dismissal. We give them twenty-one days to settle before we file at the National Industrial Court in Lagos.",
            ),
            (
                "Speaker 2",
                "O ṣe. I will send the contract, payslips, and the termination email this evening. Keep the without-prejudice settlement talk I had with HR off anything you write — they offered a small package orally.",
            ),
            (
                "Speaker 1",
                "That stays off the record. Demand letter only uses the contractual figures. If they do not settle, we file. I will diarise the filing checkpoint for the third of October.",
            ),
            ("Speaker 2", "Perfect. Can we speak again once you have the draft, before it goes out?"),
            (
                "Speaker 1",
                "Yes — Friday morning. Send the documents tonight and I will circulate the draft demand for your approval before service.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Client call — Adeyemi & Co, Lagos employment notice review",
        "source": "omi",
        "language_hint": "en-yo",
        "detected_language": "multilingual",
        "client_name": "Adeyemi & Co",
        "speakers": {"Speaker 1": "Adv. Folake Adeyemi", "Speaker 2": "Tunde Okonkwo"},
        "flags": [
            _flag_near(segments, 1, "Termination without three months' notice"),
            _flag_near(segments, 6, "NICN filing if no settlement — 3 October"),
        ],
        "segments": segments,
        "redact_indexes": [5],
        "generate": True,
    }


def _dlamini_joburg() -> dict[str, Any]:
    segments = _timed(
        [
            (
                "Speaker 1",
                "Sawubona, Thandi. This conversation is privileged. The landlord seeks eviction from the Hillbrow flat — what notice did you receive?",
            ),
            (
                "Speaker 2",
                "Ngiyabonga, advocate. They taped a letter on the door only. No personal service, no sheriff. Rent is two months behind because of the factory shutdown, not because I refuse to pay.",
            ),
            (
                "Speaker 1",
                "Under PIE we can challenge defective service of the section four notice. Inkantolo must also see your payment history and the reason for the arrears.",
            ),
            (
                "Speaker 2",
                "I can pay half the arrears by Friday if they stop any lock-out. I still work night shifts — I need to stay in that flat until the factory takes me back.",
            ),
            (
                "Speaker 1",
                "We will apply for an interim stay at the Johannesburg Magistrates' Court and put a payment proposal on record. Bring bank statements and the taped notice photo.",
            ),
            (
                "Speaker 2",
                "Please keep my sister's medical situation out of any affidavit. That is family business, not for the landlord's attorneys.",
            ),
            (
                "Speaker 1",
                "Noted — that stays off the record. I will draft the stay papers, the answering affidavit on service, and diarise a return date for next Wednesday.",
            ),
            (
                "Speaker 2",
                "Ngiyezwa. I will WhatsApp the photos tonight and bring the statements tomorrow morning.",
            ),
            (
                "Speaker 1",
                "Good. Do not hand over keys and do not sign anything from the landlord without calling me first.",
            ),
        ],
        builder=_sahara,
        pace=2.1,
    )
    return {
        "title": "Mention notes — Dlamini, Johannesburg eviction defence",
        "source": "mic",
        "language_hint": "en-zu",
        "detected_language": "multilingual",
        "client_name": "Thandi Dlamini",
        "speakers": {"Speaker 1": "Adv. Sipho Nkosi", "Speaker 2": "Thandi Dlamini"},
        "flags": [
            _flag_near(segments, 1, "Section 4 notice — service disputed"),
            _flag_near(segments, 4, "Interim stay application"),
        ],
        "segments": segments,
        "redact_indexes": [5],
        "generate": True,
    }


SESSIONS: list[dict[str, Any]] = [
    _wanjiru_showcase(),
    _wanjiru_voice_memo(),
    _otieno_court(),
    _otieno_briefing(),
    _coastal_strategy(),
    _coastal_nyali(),
    _githunguri_intake(),
    _githunguri_followup(),
    _barclays_apex(),
    _karanja_meeting(),
    _karanja_site(),
    _riverside_court(),
    _sahara_milimani(),
    _bello_kano(),
    _adeyemi_lagos(),
    _dlamini_joburg(),
]
