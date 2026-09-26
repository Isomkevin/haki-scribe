"""Tenant-isolated session APIs used after production authentication is enabled.

The original /sessions API remains the intentionally separate demo path. These
routes never read from the in-memory demo store and always verify firm context.
"""
from __future__ import annotations

import uuid
import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.models.schemas import (
    ActionResult,
    DetectedAction,
    FlagCreate,
    FlaggedMoment,
    SegmentRedactRequest,
    Session,
    SessionCreate,
    SessionDetail,
    SessionStatus,
    SpeakerRelabelRequest,
    TranscriptSegment,
)
from app.services.production_auth import require_csrf
from app.services.production_auth import require_production_user
from app.services import transcription
from app.services.tenant_context import (
    production_client,
    require_organisation,
    require_session_access,
    require_workspace_administrator,
    require_workspace,
)

router = APIRouter()

RecordType = Literal["segment", "flag", "action", "result", "chat", "contact"]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class SessionRecordCreate(BaseModel):
    record_type: RecordType
    payload: dict[str, Any]


class SessionStatusUpdate(BaseModel):
    status: SessionStatus


def _to_session(row: dict[str, Any]) -> Session:
    return Session(
        id=row["id"],
        title=row["title"],
        source=row["source"],
        language_hint=row.get("language_hint"),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def append_record(client, session_id: uuid.UUID, user_id: str, record_type: RecordType, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.table("haki_session_records").insert({
        "session_id": str(session_id), "record_type": record_type,
        "payload": payload, "created_by": user_id,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not save session record")
    return response.data[0]


def session_detail(client, row: dict[str, Any]) -> SessionDetail:
    """Rebuild the current session view from its append-only tenant records."""
    response = client.table("haki_session_records").select("record_type,payload").eq("session_id", row["id"]).order("created_at").execute()
    transcript_by_id: dict[str, TranscriptSegment] = {}
    flags: list[FlaggedMoment] = []
    actions: dict[str, DetectedAction] = {}
    results: dict[str, ActionResult] = {}
    for record in response.data or []:
        payload = record.get("payload") or {}
        try:
            if record["record_type"] == "segment":
                segment = TranscriptSegment(**payload)
                transcript_by_id[str(segment.id)] = segment
            elif record["record_type"] == "flag":
                flags.append(FlaggedMoment(**payload))
            elif record["record_type"] == "action":
                action = DetectedAction(**payload)
                actions[str(action.id)] = action
            elif record["record_type"] == "result":
                result = ActionResult(**payload)
                results[str(result.action_id)] = result
        except (TypeError, ValueError):
            # Corrupt records are retained for audit but never crash a user's
            # workspace view; operational monitoring should investigate them.
            continue
    return SessionDetail(
        **_to_session(row).model_dump(), transcript=list(transcript_by_id.values()),
        flagged_moments=flags, detected_actions=list(actions.values()), action_results=list(results.values()),
    )


@router.websocket("/{session_id}/stream")
async def stream_audio(
    websocket: WebSocket,
    session_id: uuid.UUID,
    organisation_id: str,
    workspace_id: str,
):
    """Live capture for a verified production session; audio is not stored here."""
    if not os.environ.get("HAKISCRIBE_PRODUCTION_AUTH", "").lower() in {"1", "true", "yes", "on"}:
        await websocket.close(code=4403)
        return
    allowed = {item.strip() for item in os.environ.get("HAKISCRIBE_ALLOWED_ORIGINS", "").split(",") if item.strip()}
    if not allowed or websocket.headers.get("origin") not in allowed:
        await websocket.close(code=4403)
        return
    try:
        user = await require_production_user(access_token=websocket.cookies.get("hakiscribe_access_token"))
        org_id = uuid.UUID(organisation_id)
        workspace_uuid = uuid.UUID(workspace_id)
        client = production_client()
        membership = client.table("haki_memberships").select("role").eq("organisation_id", str(org_id)).eq("user_id", user.id).eq("status", "active").execute()
        if not membership.data:
            raise HTTPException(status_code=403, detail="No organisation access")
        row = require_session_access(client, session_id, org_id, user.id)
        if row["workspace_id"] != str(workspace_uuid):
            raise HTTPException(status_code=404, detail="Session not found")
    except (ValueError, HTTPException):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    provider = transcription.get_provider()
    elapsed_ms = 0
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            chunk_ms = 3000
            result = await provider.transcribe_chunk(audio_bytes, language_hint=row.get("language_hint"))
            if not (result.text or "").strip():
                elapsed_ms += chunk_ms
                continue
            detail = session_detail(client, row)
            speaker = detail.transcript[-1].speaker if detail.transcript and detail.transcript[-1].speaker else "Speaker 1"
            segment = TranscriptSegment(session_id=session_id, speaker=speaker, text=result.text.strip(), start_ms=elapsed_ms, end_ms=elapsed_ms + chunk_ms, confidence=result.confidence, source_raw=result.raw)
            append_record(client, session_id, user.id, "segment", segment.model_dump(mode="json"))
            elapsed_ms += chunk_ms
            await websocket.send_json(segment.model_dump(mode="json"))
    except WebSocketDisconnect:
        return


@router.post("/workspaces", status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    context=Depends(require_workspace_administrator),
    _csrf: None = Depends(require_csrf),
):
    """Create a workspace within the selected firm."""
    user, organisation_id = context
    client = production_client()
    response = client.table("haki_workspaces").insert({
        "organisation_id": str(organisation_id),
        "name": payload.name.strip(),
        "created_by": user.id,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not create workspace")
    client.table("haki_audit_events").insert({
        "organisation_id": str(organisation_id),
        "actor_id": user.id,
        "event_type": "workspace_created",
        "target_type": "workspace",
        "target_id": response.data[0]["id"],
    }).execute()
    return response.data[0]


@router.get("/workspaces")
async def list_workspaces(context=Depends(require_organisation)):
    """List only workspaces belonging to the verified firm."""
    _, organisation_id = context
    response = (
        production_client().table("haki_workspaces").select("*")
        .eq("organisation_id", str(organisation_id)).order("name").execute()
    )
    return response.data or []


@router.post("", response_model=Session, status_code=201)
async def create_session(
    payload: SessionCreate,
    context=Depends(require_workspace),
    _csrf: None = Depends(require_csrf),
):
    """Create a session in a workspace proven to belong to the current firm."""
    user, organisation_id, workspace_id = context
    session = Session(title=payload.title.strip(), source=payload.source, language_hint=payload.language_hint)
    client = production_client()
    response = client.table("haki_sessions").insert({
        "id": str(session.id),
        "organisation_id": str(organisation_id),
        "workspace_id": str(workspace_id),
        "created_by": user.id,
        "title": session.title,
        "source": session.source.value,
        "status": session.status.value,
        "language_hint": session.language_hint,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not create session")
    client.table("haki_audit_events").insert({
        "organisation_id": str(organisation_id), "actor_id": user.id,
        "event_type": "session_created", "target_type": "session", "target_id": str(session.id),
    }).execute()
    return _to_session(response.data[0])


@router.get("", response_model=list[Session])
async def list_sessions(context=Depends(require_workspace)):
    """List sessions visible to the active user, including matter restrictions."""
    user, organisation_id, workspace_id = context
    client = production_client()
    response = (
        client.table("haki_sessions").select("*")
        .eq("organisation_id", str(organisation_id)).eq("workspace_id", str(workspace_id))
        .order("created_at", desc=True).execute()
    )
    visible: list[Session] = []
    for row in response.data or []:
        try:
            require_session_access(client, uuid.UUID(row["id"]), organisation_id, user.id)
            visible.append(_to_session(row))
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
    return visible


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, context=Depends(require_organisation)):
    user, organisation_id = context
    row = require_session_access(production_client(), session_id, organisation_id, user.id)
    return session_detail(production_client(), row)


@router.post("/{session_id}/flags", response_model=FlaggedMoment, status_code=201)
async def create_flag(
    session_id: uuid.UUID,
    payload: FlagCreate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    flag = FlaggedMoment(session_id=session_id, at_ms=payload.at_ms, label=payload.label)
    append_record(client, session_id, user.id, "flag", flag.model_dump(mode="json"))
    return flag


@router.post("/{session_id}/speakers", response_model=list[TranscriptSegment])
async def relabel_speakers(
    session_id: uuid.UUID,
    payload: SpeakerRelabelRequest,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    detail = session_detail(client, row)
    for segment in detail.transcript:
        if segment.speaker in payload.mapping:
            segment.speaker = payload.mapping[segment.speaker]
            append_record(client, session_id, user.id, "segment", segment.model_dump(mode="json"))
    return session_detail(client, row).transcript


@router.patch("/{session_id}/segments/{segment_id}", response_model=TranscriptSegment)
async def update_segment(
    session_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentRedactRequest,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    client = production_client()
    row = require_session_access(client, session_id, organisation_id, user.id)
    segment = next((item for item in session_detail(client, row).transcript if item.id == segment_id), None)
    if segment is None:
        raise HTTPException(status_code=404, detail="Transcript segment not found")
    if payload.redacted is not None:
        segment.redacted = payload.redacted
    if payload.text is not None:
        segment.text = payload.text.strip()
    append_record(client, session_id, user.id, "segment", segment.model_dump(mode="json"))
    return segment


@router.post("/{session_id}/finalize", response_model=Session)
async def finalize_session(session_id: uuid.UUID, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    response = client.table("haki_sessions").update({"status": SessionStatus.ready.value}).eq("id", str(session_id)).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not finalize session")
    return _to_session(response.data[0])


@router.patch("/{session_id}/status", response_model=Session)
async def update_session_status(
    session_id: uuid.UUID,
    payload: SessionStatusUpdate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    response = client.table("haki_sessions").update({"status": payload.status.value}).eq("id", str(session_id)).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not update session")
    return _to_session(response.data[0])


@router.post("/{session_id}/records", status_code=201)
async def append_session_record(
    session_id: uuid.UUID,
    payload: SessionRecordCreate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    """Append an immutable transcript/flag/action/result/chat/contact record."""
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    return append_record(client, session_id, user.id, payload.record_type, payload.payload)


@router.get("/{session_id}/records")
async def list_session_records(session_id: uuid.UUID, context=Depends(require_organisation)):
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    response = client.table("haki_session_records").select("*").eq("session_id", str(session_id)).order("created_at").execute()
    return response.data or []
