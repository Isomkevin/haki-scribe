"""Virtual court platform adapters (authorized APIs only)."""

from app.services.court_adapters.base import CourtAdapter, HearingEvent
from app.services.court_adapters.calendar_adapter import GoogleCalendarAdapter
from app.services.court_adapters.teams_adapter import TeamsGraphAdapter
from app.services.court_adapters.zoom_adapter import ZoomAdapter

__all__ = [
    "CourtAdapter",
    "HearingEvent",
    "GoogleCalendarAdapter",
    "TeamsGraphAdapter",
    "ZoomAdapter",
]
