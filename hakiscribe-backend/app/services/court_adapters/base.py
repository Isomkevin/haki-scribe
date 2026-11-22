from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class HearingEvent:
    external_id: str
    title: str
    description: str = ""
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    meeting_url: Optional[str] = None
    court_name: Optional[str] = None
    case_reference: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CourtAdapter(ABC):
    source: str

    @abstractmethod
    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        ...

    @abstractmethod
    def configured(self) -> bool:
        ...

    def capability_notes(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "live_bot_join": False,
            "recording_download": False,
            "stage": "A",
        }
