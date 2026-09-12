"""Seed the running HakiScribe backend with realistic demo sessions.

Usage:
    python seed_demo.py [base_url]

Defaults to the deployed Render backend. Safe to re-run: it creates new
sessions each time (storage is in-memory and resets on redeploy anyway).
"""

import os
import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "HAKISCRIBE_API", "https://hakiscribe-backend.onrender.com")).rstrip("/")
OMI_SECRET = os.environ.get("OMI_SHARED_SECRET", "")


def seg(speaker, text, start_s, dur_s=6):
    return {
        "speaker": speaker,
        "text": text,
        "start_ms": int(start_s * 1000),
        "end_ms": int((start_s + dur_s) * 1000),
        "confidence": 0.94,
    }


MATTERS = [
    {"client_name": "Wanjiru Holdings Ltd", "matter_name": "Wanjiru Holdings v. Sarova Contractors — construction defect"},
    {"client_name": "Achieng' Otieno", "matter_name": "Otieno — employment termination claim"},
    {"client_name": "Mombasa Coastal Sacco", "matter_name": "Coastal Sacco — loan recovery portfolio"},
]

SESSIONS = [
    {
        "title": "Client meeting — Wanjiru Holdings, defective works at Kilimani site",
        "source": "omi",
        "language_hint": "code-switch",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "James Wanjiru"},
        "flags": [{"at_ms": 192000, "label": "Payment withheld — key fact"},
                  {"at_ms": 356000, "label": "Deadline for demand letter"}],
        "segments": [
            seg("Speaker 1", "Thanks for coming in, James. Before we start — this conversation is privileged. Take me through what happened at the Kilimani site.", 0, 9),
            seg("Speaker 2", "Sarova Contractors were meant to complete the slab works by the fifteenth of June. By July the slab had visible cracking on the second floor.", 9, 11),
            seg("Speaker 1", "Did you raise it with them in writing?", 20, 4),
            seg("Speaker 2", "Yes, twice. Email on the second of July, then a WhatsApp on the eighteenth. They said they would send an engineer, hakuna kitu ilifanyika.", 24, 12),
            seg("Speaker 1", "And the contract sum? What has been paid so far?", 36, 5),
            seg("Speaker 2", "Contract was eighteen million shillings. We have paid twelve point six million. We withheld the balance after the cracking.", 41, 11),
            seg("Speaker 2", "The structural engineer, Eng. Mutiso, says remedial works will cost about four point two million.", 52, 9),
            seg("Speaker 1", "Good. That gives us a quantified loss. I want to send a formal demand letter to Sarova Contractors before we consider arbitration under clause 41.", 61, 13),
            seg("Speaker 2", "How long do they get?", 74, 3),
            seg("Speaker 1", "Twenty-one days. If they don't respond we file a notice of arbitration. Let's also diarise a follow-up meeting on the third of October at ten in the morning.", 77, 14),
            seg("Speaker 2", "That works. Also, please keep the bit about my partner's tax position out of anything you write.", 91, 8),
            seg("Speaker 1", "Noted — that stays off the record. I'll get the demand letter to you for review by Friday.", 99, 8),
        ],
        "redact_indexes": [10],
        "generate": True,
    },
    {
        "title": "Court proceeding — Employment & Labour Relations Court, Otieno termination",
        "source": "mic",
        "language_hint": "en",
        "speakers": {"Speaker 1": "Hon. Justice Mwangi", "Speaker 2": "Adv. Naomi Kariuki", "Speaker 3": "Adv. Peter Ochieng"},
        "flags": [{"at_ms": 145000, "label": "Court directions — filing dates"}],
        "segments": [
            seg("Speaker 1", "Cause number forty-two of this year, Achieng' Otieno versus Bidii Logistics Limited. Appearances please.", 0, 9),
            seg("Speaker 2", "Kariuki for the claimant, my lord.", 9, 4),
            seg("Speaker 3", "Ochieng' for the respondent.", 13, 3),
            seg("Speaker 2", "My lord, the claimant was summarily dismissed on the ninth of March without a show cause letter and without a hearing, contrary to section forty-one of the Employment Act.", 16, 14),
            seg("Speaker 3", "My lord, the respondent's position is that the claimant abandoned duty for eleven consecutive days.", 30, 9),
            seg("Speaker 1", "Counsel, has the respondent filed a replying affidavit?", 39, 5),
            seg("Speaker 3", "Not yet, my lord. We seek fourteen days.", 44, 4),
            seg("Speaker 1", "The respondent shall file and serve a replying affidavit within fourteen days. The claimant may file a supplementary affidavit within seven days thereafter.", 48, 13),
            seg("Speaker 1", "Mention on the twenty-eighth of October at nine o'clock for further directions. Highlighting of submissions thereafter.", 61, 10),
            seg("Speaker 2", "Much obliged, my lord.", 71, 3),
        ],
        "redact_indexes": [],
        "generate": True,
    },
    {
        "title": "Client call — Mombasa Coastal Sacco, defaulted loan recovery strategy",
        "source": "omi",
        "language_hint": "code-switch",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Fatuma Said (CEO, Coastal Sacco)"},
        "flags": [{"at_ms": 88000, "label": "Statutory notice timeline"}],
        "segments": [
            seg("Speaker 1", "Fatuma, you mentioned three accounts in default. Give me the worst one first.", 0, 7),
            seg("Speaker 2", "Mwakio Enterprises. Four point eight million outstanding, last payment was in November. Security is a title in Nyali, LR number Mombasa slash Block Twelve slash three four one.", 7, 15),
            seg("Speaker 1", "Have you issued a statutory notice under section ninety of the Land Act?", 22, 6),
            seg("Speaker 2", "Hapana, not yet. We only sent internal reminder letters.", 28, 5),
            seg("Speaker 1", "Then we start there — a three months' statutory notice, then the forty days' notification before sale. I'll prepare the section ninety notice this week.", 33, 13),
            seg("Speaker 2", "And the other two? Kadzo Traders is about nine hundred thousand, unsecured.", 46, 7),
            seg("Speaker 1", "For unsecured, a demand then a plaint in the Magistrate's Court. Let's open a recovery matter for the Sacco portfolio so everything sits in one file.", 53, 13),
            seg("Speaker 2", "Please do. Can we meet on the twentieth of September at two p.m. to review all three?", 66, 8),
            seg("Speaker 1", "Twentieth at two works. I'll circulate a status note before then.", 74, 7),
        ],
        "redact_indexes": [],
        "generate": False,
    },
    {
        "title": "Intake — new client, land succession dispute in Kiambu",
        "source": "mic",
        "language_hint": "code-switch",
        "speakers": {"Speaker 1": "Adv. Naomi Kariuki", "Speaker 2": "Grace Njeri"},
        "flags": [{"at_ms": 52000, "label": "Limitation concern"}],
        "segments": [
            seg("Speaker 1", "Grace, tell me about the land and who is currently on the title.", 0, 6),
            seg("Speaker 2", "My late father's parcel in Kiambu, Githunguri. He died in twenty-nineteen. My brother obtained letters of administration and transferred two acres to himself.", 6, 15),
            seg("Speaker 1", "Were you listed as a beneficiary in the petition?", 21, 5),
            seg("Speaker 2", "No. He said I was married so sitakuwa na haki. My mother and two sisters were also left out.", 26, 9),
            seg("Speaker 1", "That's not the law. Under the Law of Succession Act a married daughter remains a beneficiary. We can apply to revoke the grant under section seventy-six.", 35, 14),
            seg("Speaker 2", "Is it too late? It's been a while.", 49, 4),
            seg("Speaker 1", "Revocation isn't strictly time-barred where the grant was obtained by concealment, but we should move quickly. Bring the death certificate, the grant, and the green card search.", 53, 15),
            seg("Speaker 2", "I'll get them next week.", 68, 3),
        ],
        "redact_indexes": [],
        "generate": False,
    },
]


def main():
    client = httpx.Client(timeout=180)
    print(f"Seeding {BASE}")

    for m in MATTERS:
        r = client.post(f"{BASE}/matters", json=m)
        print("matter", r.status_code, r.json().get("matter_name") if r.is_success else r.text[:200])

    for spec in SESSIONS:
        r = client.post(f"{BASE}/sessions", json={
            "title": spec["title"], "source": spec["source"],
            "language_hint": spec["language_hint"]})
        r.raise_for_status()
        sid = r.json()["id"]
        print("\nsession", sid, spec["title"][:60])

        headers = {"x-omi-secret": OMI_SECRET} if OMI_SECRET else {}
        r = client.post(f"{BASE}/webhooks/omi", headers=headers,
                        json={"session_external_id": sid, "segments": spec["segments"]})
        print("  transcript", r.status_code, r.text[:120])

        for f in spec["flags"]:
            client.post(f"{BASE}/sessions/{sid}/flags", json=f)
        print("  flags", len(spec["flags"]))

        client.post(f"{BASE}/sessions/{sid}/speakers", json={"mapping": spec["speakers"]})

        detail = client.get(f"{BASE}/sessions/{sid}").json()
        segments = detail["transcript"]
        for idx in spec["redact_indexes"]:
            if idx < len(segments):
                client.patch(f"{BASE}/sessions/{sid}/segments/{segments[idx]['id']}",
                             json={"redacted": True})
        print("  redacted", len(spec["redact_indexes"]))

        client.post(f"{BASE}/sessions/{sid}/finalize")
        t0 = time.time()
        r = client.post(f"{BASE}/sessions/{sid}/detect")
        actions = r.json() if r.is_success else []
        print(f"  detected {len(actions)} actions in {time.time() - t0:.1f}s")

        if spec["generate"] and actions:
            ids = [a["id"] for a in actions if a.get("pre_checked")] or [a["id"] for a in actions[:2]]
            r = client.post(f"{BASE}/sessions/{sid}/generate", json={"action_ids": ids})
            print("  generated", r.status_code, len(r.json()) if r.is_success else r.text[:200])

    print("\nLibrary:", len(client.get(f"{BASE}/sessions").json()), "sessions")


if __name__ == "__main__":
    main()
