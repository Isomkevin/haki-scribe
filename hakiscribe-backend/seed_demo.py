"""Seed the running HakiScribe backend with realistic demo sessions.

Usage:
    python seed_demo.py [base_url]

Defaults to the deployed Render backend. Safe to re-run: existing titles
are reused. Prefers POST /demo/sync on current backends; falls back to
the original HTTP path for older deploys.
"""

import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.demo_catalog import MATTERS, SESSIONS

BASE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "HAKISCRIBE_API", "https://hakiscribe-backend.onrender.com")).rstrip("/")
OMI_SECRET = os.environ.get("OMI_SHARED_SECRET", "")


def main():
    client = httpx.Client(timeout=600)
    print(f"Seeding {BASE}")

    try:
        r = client.post(f"{BASE}/demo/sync")
        if r.status_code < 400:
            payload = r.json()
            print(
                f"Synced via /demo/sync — created {payload.get('created')} "
                f"reused {payload.get('reused')} completing={payload.get('completing')}"
            )
            print("Library:", len(payload.get("sessions") or []), "sessions")
            return
        print("  /demo/sync unavailable:", r.status_code, r.text[:200])
    except httpx.HTTPError as exc:
        print("  /demo/sync failed:", exc)

    existing = {item.get("title") for item in client.get(f"{BASE}/sessions").json()}
    known_matters = {item.get("matter_name") for item in client.get(f"{BASE}/matters").json()}

    for m in MATTERS:
        if m["matter_name"] in known_matters:
            print("matter exists", m["matter_name"])
            continue
        r = client.post(f"{BASE}/matters", json=m)
        print("matter", r.status_code, r.json().get("matter_name") if r.is_success else r.text[:200])

    for spec in SESSIONS:
        if spec["title"] in existing:
            print("\nsession exists", spec["title"][:60])
            continue
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
