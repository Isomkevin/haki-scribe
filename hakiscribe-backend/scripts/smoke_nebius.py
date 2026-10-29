#!/usr/bin/env python3
"""Live Nebius smoke: Kiswahili/English intake with a privileged line.

Fails if the privileged marker appears in any model output captured here.
Requires NEBIUS_API_KEY (and optionally TAVILY_API_KEY).

Usage (from hakiscribe-backend/):
  python scripts/smoke_nebius.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MARKER = "ZEBRA-PRIVILEGED-7731"


async def main() -> int:
    key = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not key:
        print("SKIP: NEBIUS_API_KEY is not set. Set it and re-run:")
        print("  set NEBIUS_API_KEY=...   # Windows")
        print("  export NEBIUS_API_KEY=...  # Unix")
        print("  python scripts/smoke_nebius.py")
        return 2

    # Seed connector store from env so nebius.creds() works without a UI save.
    from app.services import integrations, nebius, tray_logic, ai_runs
    from types import SimpleNamespace
    import uuid

    integrations._connections["nebius"] = {
        "provider_id": "nebius",
        "connected_at": "smoke",
        "creds": {
            "api_key": key,
            "base_url": os.environ.get("NEBIUS_BASE_URL", "").strip() or nebius.DEFAULT_BASE_URL,
            "ultra_model": os.environ.get("NEMOTRON_ULTRA_MODEL") or os.environ.get("NEBIUS_ULTRA_MODEL") or "",
            "super_model": os.environ.get("NEMOTRON_SUPER_MODEL") or os.environ.get("NEBIUS_SUPER_MODEL") or "",
            "nano_model": os.environ.get("NEMOTRON_NANO_MODEL") or os.environ.get("NEBIUS_NANO_MODEL") or "",
        },
    }
    ai_runs.clear()

    print("a) GET /v1/models …")
    models = await nebius.list_models(force=True)
    nemotron = [m for m in models if "nemotron" in m.lower()]
    print(f"   models={len(models)} nemotron={len(nemotron)}")
    print("   sample:", ", ".join(nemotron[:8]) or "(none)")
    tiers = await nebius.resolve_tiers()
    print("   resolved:", tiers)
    if not tiers.get("super"):
        print("FAIL: could not resolve Super tier")
        return 1

    segments = [
        SimpleNamespace(
            id=uuid.uuid4(),
            speaker="Advocate",
            text="Achieng', asante kwa kuja. Mahakama imeweka mention on the twenty-eighth of October.",
            redacted=False,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            speaker="Client",
            text=f"Off record partner tax discussion: {MARKER}",
            redacted=True,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            speaker="Advocate",
            text="Bidii Logistics must file a response and replying affidavit within fourteen days.",
            redacted=False,
        ),
    ]
    block = tray_logic.build_transcript_block(segments)
    assert MARKER not in block, "privileged marker leaked into transcript block"

    print("b) action-tray (detection) on Super …")
    system = (
        "Return ONLY a JSON object {\"actions\":[...]} with type, title, preview, "
        "confidence, source_quote from the transcript. Do not invent facts."
    )
    result = await nebius.complete(
        "super",
        system,
        f"Transcript:\n{block}",
        task="detection",
        json_mode=True,
        privileged_lines_excluded=1,
    )
    print("   model=", result["model"], "latency_ms=", result["latency_ms"])
    print("   text_trim=", (result["text"] or "")[:400])
    if MARKER in (result["text"] or "") or MARKER in (result.get("json_text") or ""):
        print("FAIL: privileged marker appeared in model output")
        return 1
    ai_runs.assert_no_marker(MARKER)

    if tiers.get("ultra"):
        print("c) generate-work sample on Ultra …")
        draft = await nebius.complete(
            "ultra",
            "Draft a short Kenyan demand letter. Use [CONFIRM: …] for missing facts. Cite only the record.",
            f"Verified transcript:\n{block}\n\nDraft a demand letter for Bidii Logistics.",
            task="draft",
            privileged_lines_excluded=1,
        )
        print("   model=", draft["model"], "latency_ms=", draft["latency_ms"])
        print("   text_trim=", (draft["text"] or "")[:500])
        if MARKER in (draft["text"] or ""):
            print("FAIL: privileged marker in draft")
            return 1
    else:
        print("c) SKIP Ultra — not resolved")

    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if tavily_key:
        print("d) legal-research via Tavily + Super …")
        from app.services import tavily

        integrations._connections["tavily"] = {
            "provider_id": "tavily",
            "connected_at": "smoke",
            "creds": {"api_key": tavily_key},
        }
        hits = await tavily.search("Kenya Civil Procedure Rules mention date", max_results=3)
        print("   tavily hits=", len(hits))
        ctx = "\n".join(f"[{i}] {h['title']} {h['url']}" for i, h in enumerate(hits, 1))
        research = await nebius.complete(
            "super",
            "Answer using ONLY the sources. Cite [1]. Label them external authorities.",
            f"Question: What is a mention date in Kenyan procedure?\n\nSources:\n{ctx}",
            task="research",
            privileged_lines_excluded=1,
        )
        print("   model=", research["model"])
        print("   text_trim=", (research["text"] or "")[:500])
    else:
        print("d) SKIP research — TAVILY_API_KEY not set")

    print("e) ai_runs rows:")
    for row in ai_runs.recent(10):
        print("  ", {k: row[k] for k in ("task", "provider", "model_id", "latency_ms", "status", "privileged_lines_excluded")})
    ai_runs.assert_no_marker(MARKER)
    print("OK: smoke passed; privileged marker never appeared in outputs or ai_runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
