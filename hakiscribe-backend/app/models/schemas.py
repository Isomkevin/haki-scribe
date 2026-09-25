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
    language_hint: Optional[str] = None  # en|sw|ha|…|code-switch|en-ha|multilingual|…



class Session(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    source: SessionSource
    language_hint: Optional[str] = None
    # Set when live captions look code-switched / multilingual (heuristic LID).
    detected_language: Optional[str] = None
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
    redacted: Optional[bool] = None
    text: Optional[str] = None


class Matter(BaseModel):
    """A persistent client/matter record — lets detection recognize a
    repeat client instead of proposing 'new matter' every session."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    client_name: str
    matter_name: str
    session_ids: list[uuid.UUID] = []
    contact_ids: list[uuid.UUID] = []
    ambiguous_deal_id: Optional[str] = None  # set once mirrored into Ambiguous CRM
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MatterCreate(BaseModel):
    client_name: str
    matter_name: str
    session_id: Optional[uuid.UUID] = None


class Contact(BaseModel):
    """A client or counterpart persisted from a workspace_matter or CRM card."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    updates: dict[str, Any] = {}
    matter_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None
    ambiguous_contact_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContactCreate(BaseModel):
    name: str
    updates: dict[str, Any] = {}
    matter_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None


class ActionType(str, Enum):
    draft_document = "draft_document"
    calendar_event = "calendar_event"
    workspace_matter = "workspace_matter"
    crm_entry = "crm_entry"
    private_note = "private_note"
    time_entry = "time_entry"
    legal_research = "legal_research"
    web_search = "web_search"
    llm_task = "llm_task"


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
    field_overrides: dict[str, dict[str, Any]] = {}  # action_id -> edited extracted_fields


class ActionResult(BaseModel):
    action_id: uuid.UUID
    type: ActionType
    status: str  # "success" | "error"
    result: dict[str, Any] = {}
    error: Optional[str] = None
    # When the artifact was produced — kept on the record so the case tracker can
    # show a date for every generated document after a restart.
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DraftDocumentResult(BaseModel):
    document_text: str
    document_kind: Optional[str] = None
    source: str = "transcript"
    ambiguous_document_id: Optional[str] = None


class CalendarEventResult(BaseModel):
    title: str
    start: str
    end: str
    description: str
    location: Optional[str] = None
    attendees: list[str] = []
    ics: str
    ambiguous_event_id: Optional[str] = None


class TimeEntryResult(BaseModel):
    duration_hours: float
    activity_description: str
    narrative: str
    matter_name: Optional[str] = None
    billable: bool = True


class ResearchSource(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    published: Optional[str] = None
    extract: Optional[str] = None
    citation: Optional[str] = None
    kind: Optional[str] = None


class ResearchResult(BaseModel):
    """Legal research or open-web background. Never merged into drafted
    legal text — always presented with its sources so the user can check."""

    question: str
    answer: str
    sources: list[ResearchSource] = []
    model: Optional[str] = None
    scope: str = "legal"  # "legal" | "web"


class LlmTaskResult(BaseModel):
    model: str
    instruction: str
    output: str


class ChatMessage(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    role: str  # "user" | "assistant"
    content: str
    model: Optional[str] = None
    error: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatThread(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    title: str = "New conversation"
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AskRequest(BaseModel):
    """Ad-hoc instruction the user types under the action tray."""

    instruction: str
    model: Optional[str] = None


class SessionLibraryItem(Session):
    """Session row as shown in the Session Library, with persisted matters/contacts."""

    matters: list[Matter] = []
    contacts: list[Contact] = []
    generated_types: list[str] = []


class SessionDetail(Session):
    transcript: list[TranscriptSegment] = []
    detected_actions: list[DetectedAction] = []
    flagged_moments: list[FlaggedMoment] = []
    action_results: list[ActionResult] = []
    matters: list[Matter] = []
    contacts: list[Contact] = []


class OmiWebhookPayload(BaseModel):
    """Shape this to match whatever Omi actually sends — check their docs
    for the live payload before the demo. This is a reasonable starting
    guess: a list of already-transcribed segments."""

    session_external_id: Optional[str] = None
    segments: list[dict[str, Any]]
