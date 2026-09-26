"""Tenant-isolated session APIs used after production authentication is enabled.

The original /sessions API remains the intentionally separate demo path. These
routes never read from the in-memory demo store and always verify firm context.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import Session, SessionCreate, SessionStatus
from app.services.production_auth import require_csrf
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


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: uuid.UUID, context=Depends(require_organisation)):
    user, organisation_id = context
    row = require_session_access(production_client(), session_id, organisation_id, user.id)
    return _to_session(row)


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
    response = client.table("haki_session_records").insert({
        "session_id": str(session_id), "record_type": payload.record_type,
        "payload": payload.payload, "created_by": user.id,
    }).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Could not save session record")
    return response.data[0]


@router.get("/{session_id}/records")
async def list_session_records(session_id: uuid.UUID, context=Depends(require_organisation)):
    user, organisation_id = context
    client = production_client()
    require_session_access(client, session_id, organisation_id, user.id)
    response = client.table("haki_session_records").select("*").eq("session_id", str(session_id)).order("created_at").execute()
    return response.data or []
