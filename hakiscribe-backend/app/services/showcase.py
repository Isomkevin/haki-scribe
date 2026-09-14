"""Build a completed Kenyan client-meeting session in-process.

Judges can open a finished Action Tray without a microphone. The Wanjiru
showcase is now one record in the full demo library — this module stays
as the judge-demo entry point.
"""

from __future__ import annotations

from app.services import demo_library

SHOWCASE_TITLE = demo_library.SHOWCASE_TITLE
SHOWCASE_SEGMENTS = next(spec["segments"] for spec in demo_library.SESSIONS if spec["title"] == SHOWCASE_TITLE)


def find_existing_showcase():
    detail = demo_library.find_session_by_title(SHOWCASE_TITLE)
    if detail and (detail.action_results or detail.detected_actions):
        return detail
    return None


async def ensure_showcase(rebuild: bool = False):
    return await demo_library.ensure_showcase(rebuild=rebuild)
