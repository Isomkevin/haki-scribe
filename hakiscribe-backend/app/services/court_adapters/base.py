from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx

# Tests inject httpx.MockTransport here; production leaves it None.
_transport: Optional[httpx.AsyncBaseTransport] = None


def http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout, transport=_transport, follow_redirects=True)


class AdapterError(RuntimeError):
    """A platform call failed for a reason the user can act on (scope, consent, not found)."""

    def __init__(self, message: str, *, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


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


@dataclass
class HearingArtifact:
    """A recording or transcript fetched from a platform through its official API."""

    kind: str  # "audio" | "transcript"
    filename: str
    data: bytes
    content_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CourtAdapter(ABC):
    source: str

    @abstractmethod
    async def list_upcoming(self, *, days: int = 14) -> list[HearingEvent]:
        ...

    @abstractmethod
    def configured(self) -> bool:
        ...

    async def fetch_artifact(self, hearing: Any, *, prefer: str = "audio") -> HearingArtifact:
        raise AdapterError(f"{self.source} does not support recording download")

    def capability_notes(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "live_bot_join": False,
            "recording_download": False,
            "stage": "A",
        }
