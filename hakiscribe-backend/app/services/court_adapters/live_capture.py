"""Shared start/stop capture for official Teams / Zoom live bots (ADR-015)."""

from __future__ import annotations

from typing import Any, Optional

from app.models.schemas import Hearing, HearingSource
from app.services.court_adapters import teams_bot, zoom_bot
from app.services.court_adapters.base import AdapterError


class CaptureError(RuntimeError):
    pass


def _store_start(store: Any, hearing_id, meta: dict[str, Any]):
    if hasattr(store, "start_capture"):
        return store.start_capture(hearing_id, meta=meta)
    from app.services import hearings as demo

    return demo.start_capture(hearing_id, meta=meta)


def _store_stop(store: Any, hearing_id, *, object_key: Optional[str] = None, meta: Optional[dict[str, Any]] = None):
    if hasattr(store, "stop_capture"):
        return store.stop_capture(hearing_id, object_key=object_key, meta=meta)
    from app.services import hearings as demo

    return demo.stop_capture(hearing_id, object_key=object_key, meta=meta)


async def start_capture(hearing: Hearing, *, store: Any = None) -> dict[str, Any]:
    from app.services import hearings as demo

    store = store or demo
    if hearing.matter_id is None:
        raise CaptureError("Confirm the matter link and enable capture before the bot joins")
    enable = ((hearing.platform_metadata or {}).get("capture") or {}).get("enabled")
    # Explicit enable flag preferred; matched hearings may start without prior flag when API is called.
    if enable is False:
        raise CaptureError("Capture is disabled for this hearing")

    source = hearing.source.value if hasattr(hearing.source, "value") else str(hearing.source)
    try:
        if source == HearingSource.teams_graph.value:
            bot = teams_bot.TeamsCallingBot()
            join = await bot.join_meeting(meeting_url=hearing.meeting_url or "", hearing_id=hearing.id)
        elif source == HearingSource.zoom.value:
            bot = zoom_bot.ZoomMeetingBot()
            ext = hearing.external_id
            join = await bot.join_meeting(
                meeting_url=hearing.meeting_url or "",
                hearing_id=hearing.id,
                meeting_number=ext,
            )
        else:
            raise CaptureError(f"Live capture is only available for Teams or Zoom hearings (got {source})")
    except AdapterError as exc:
        raise CaptureError(str(exc)) from exc

    updated = _store_start(store, hearing.id, {"enabled": True, **join})
    return {"hearing": updated.model_dump(mode="json"), "capture": join}


async def stop_capture(hearing: Hearing, *, store: Any = None) -> dict[str, Any]:
    from app.services import hearings as demo

    store = store or demo
    capture = (hearing.platform_metadata or {}).get("capture") or {}
    source = hearing.source.value if hasattr(hearing.source, "value") else str(hearing.source)
    leave: dict[str, Any] = {}
    try:
        if source == HearingSource.teams_graph.value:
            call_id = capture.get("call_id")
            if call_id:
                leave = await teams_bot.TeamsCallingBot().leave_meeting(call_id=str(call_id))
        elif source == HearingSource.zoom.value:
            number = capture.get("meeting_number") or hearing.external_id
            if number:
                leave = await zoom_bot.ZoomMeetingBot().leave_meeting(meeting_number=str(number))
    except AdapterError as exc:
        raise CaptureError(str(exc)) from exc

    updated = _store_stop(store, hearing.id, meta=leave)
    return {"hearing": updated.model_dump(mode="json"), "capture": leave}
