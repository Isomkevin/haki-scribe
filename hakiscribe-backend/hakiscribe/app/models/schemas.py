import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionSource(str, Enum):
    mic = "mic"
    omi = "omi"


class SessionStatus(str, Enum):
    recording = "recording"
    processing = "processing"
    ready = "ready"
    exported = "exported"


class SessionCreate(BaseModel):
    title: str
    source: SessionSource
    language_hint: Optional[str] = None  # "en", "sw", "code-switch"


class Session(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    source: SessionSource
    language_hint: Optional[str] = None
    status: SessionStatus = SessionStatus.recording
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TranscriptSegment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    speaker: Optional[str] = None
    text: str
    start_ms: int
    end_ms: int
    confidence: Optional[float] = None
    source_raw: Optional[dict[str, Any]] = None
    redacted: bool = False  # excluded from detection — privilege/off-record control


class FlaggedMoment(BaseModel):
    """A no-look bookmark the user drops during recording (tap 'Flag this
    moment'). Biases detection toward what the user already knew mattered."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    at_ms: int
    label: Optional[str] = None  # optional short tag, e.g. "Contract terms"


class FlagCreate(BaseModel):
    at_ms: int
    label: Optional[str] = None


class SpeakerRelabelRequest(BaseModel):
    mapping: dict[str, str]  # {"Speaker 1": "John Kamau", "Speaker 2": "Mercy Wairimu"}


class SegmentRedactRequest(BaseModel):
    redacted: bool


class Matter(BaseModel):
    """A persistent client/matter record — lets detection recognize a
    repeat client instead of proposing 'new matter' every session."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    client_name: str
    matter_name: str
    ambiguous_deal_id: Optional[str] = None  # set once mirrored into Ambiguous CRM
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MatterCreate(BaseModel):
    client_name: str
    matter_name: str


class ActionType(str, Enum):
    draft_document = "draft_document"
    calendar_event = "calendar_event"
    workspace_matter = "workspace_matter"
    crm_entry = "crm_entry"
    private_note = "private_note"
    time_entry = "time_entry"


class ActionStatus(str, Enum):
    detected = "detected"
    generated = "generated"
    dismissed = "dismissed"
    error = "error"


class DetectedAction(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    type: ActionType
    title: str
    preview: str
    confidence: float
    confidence_reason: Optional[str] = None  # "Explicitly stated" | "Inferred from context"
    source_segment_id: Optional[uuid.UUID] = None  # for "View source" jump-to-transcript
    extracted_fields: dict[str, Any] = {}
    pre_checked: bool = True
    status: ActionStatus = ActionStatus.detected


class GenerateActionsRequest(BaseModel):
    action_ids: list[uuid.UUID]


class ActionResult(BaseModel):
    action_id: uuid.UUID
    type: ActionType
    status: str  # "success" | "error"
    result: dict[str, Any] = {}
    error: Optional[str] = None


class SessionDetail(Session):
    transcript: list[TranscriptSegment] = []
    detected_actions: list[DetectedAction] = []
    flagged_moments: list[FlaggedMoment] = []


class OmiWebhookPayload(BaseModel):
    """Shape this to match whatever Omi actually sends — check their docs
    for the live payload before the demo. This is a reasonable starting
    guess: a list of already-transcribed segments."""

    session_external_id: Optional[str] = None
    segments: list[dict[str, Any]]
