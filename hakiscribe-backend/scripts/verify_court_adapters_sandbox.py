#!/usr/bin/env python3
"""Live Zoom/Teams sandbox probe. Skips unless HAKISCRIBE_VERIFY_ZOOM/TEAMS=1."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def _probe_zoom() -> None:
    from app.services.court_adapters.zoom_adapter import ZoomAdapter

    adapter = ZoomAdapter()
    print("Zoom configured:", adapter.configured())
    print("Capabilities:", adapter.capability_notes())
    if not adapter.configured():
        print("FAIL: Zoom OAuth not connected")
        return
    events = await adapter.list_upcoming(days=14)
    print(f"PASS: Zoom list_upcoming → {len(events)} meeting(s)")
    for ev in events[:5]:
        print(f"  - {ev.external_id}: {ev.title[:80]}")


async def _probe_teams() -> None:
    from app.services.court_adapters.teams_adapter import TeamsGraphAdapter

    adapter = TeamsGraphAdapter()
    print("Teams configured:", adapter.configured())
    print("Capabilities:", adapter.capability_notes())
    if not adapter.configured():
        print("FAIL: Teams Graph not connected")
        return
    events = await adapter.list_upcoming(days=14)
    print(f"PASS: Teams list_upcoming → {len(events)} meeting(s)")
    for ev in events[:5]:
        print(f"  - {ev.external_id}: {ev.title[:80]}")


async def _probe_bots() -> None:
    from app.services.court_adapters import teams_bot, zoom_bot

    tb = teams_bot.TeamsCallingBot()
    zb = zoom_bot.ZoomMeetingBot()
    print("Teams bot configured:", tb.configured(), tb.capability_notes())
    print("Zoom bot configured:", zb.configured(), zb.capability_notes())


async def main() -> int:
    zoom = os.environ.get("HAKISCRIBE_VERIFY_ZOOM", "").lower() in ("1", "true", "yes")
    teams = os.environ.get("HAKISCRIBE_VERIFY_TEAMS", "").lower() in ("1", "true", "yes")
    if not zoom and not teams:
        print("SKIP: set HAKISCRIBE_VERIFY_ZOOM=1 and/or HAKISCRIBE_VERIFY_TEAMS=1")
        await _probe_bots()
        return 0
    if zoom:
        await _probe_zoom()
    if teams:
        await _probe_teams()
    await _probe_bots()
    print("Paste outcomes into 09-testing-and-verification.md (1B). Do not mark verified without real runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
