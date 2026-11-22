"""Virtual court platform adapters (authorized APIs only)."""

from app.services.court_adapters.base import AdapterError, CourtAdapter, HearingArtifact, HearingEvent
from app.services.court_adapters.calendar_adapter import GoogleCalendarAdapter
from app.services.court_adapters import live_capture, teams_bot, zoom_bot
from app.services.court_adapters.teams_adapter import TeamsGraphAdapter
from app.services.court_adapters.zoom_adapter import ZoomAdapter

__all__ = [
    "AdapterError",
    "CourtAdapter",
    "HearingArtifact",
    "HearingEvent",
    "GoogleCalendarAdapter",
    "TeamsGraphAdapter",
    "ZoomAdapter",
    "live_capture",
    "teams_bot",
    "zoom_bot",
]
