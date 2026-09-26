"""Tenant-backed session conversations stored as append-only chat records."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.schemas import ChatMessage, ChatThread
from app.routers.production_sessions import append_record, session_detail
from app.services import chat
from app.services.production_auth import require_csrf
from app.services.tenant_context import production_client, require_organisation, require_session_access

router = APIRouter()


class ThreadCreate(BaseModel):
    title: Optional[str] = None


class MessageCreate(BaseModel):
    content: str
    model: Optional[str] = None


def _threads(client, row: dict) -> list[ChatThread]:
    records = client.table("haki_session_records").select("payload").eq("session_id", row["id"]).eq("record_type", "chat").order("created_at").execute()
    current: dict[str, ChatThread] = {}
    for record in records.data or []:
        payload = record.get("payload") or {}
        if payload.get("deleted"):
            current.pop(str(payload.get("id")), None)
            continue
        try:
            thread = ChatThread(**payload)
            current[str(thread.id)] = thread
        except (TypeError, ValueError):
            continue
    return list(current.values())


def _session(client, session_id: uuid.UUID, context):
    user, organisation_id = context
    return user, require_session_access(client, session_id, organisation_id, user.id)


@router.get("/{session_id}/chats", response_model=list[ChatThread])
async def list_threads(session_id: uuid.UUID, context=Depends(require_organisation)):
    client = production_client()
    _, row = _session(client, session_id, context)
    return _threads(client, row)


@router.post("/{session_id}/chats", response_model=ChatThread)
async def create_thread(session_id: uuid.UUID, payload: ThreadCreate, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    client = production_client()
    user, row = _session(client, session_id, context)
    thread = ChatThread(session_id=session_id, title=(payload.title or "New conversation").strip()[:80])
    append_record(client, session_id, user.id, "chat", thread.model_dump(mode="json"))
    return thread


@router.get("/{session_id}/chats/{thread_id}", response_model=ChatThread)
async def get_thread(session_id: uuid.UUID, thread_id: uuid.UUID, context=Depends(require_organisation)):
    client = production_client()
    _, row = _session(client, session_id, context)
    thread = next((item for item in _threads(client, row) if item.id == thread_id), None)
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


@router.delete("/{session_id}/chats/{thread_id}")
async def delete_thread(session_id: uuid.UUID, thread_id: uuid.UUID, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    client = production_client()
    user, row = _session(client, session_id, context)
    if not any(item.id == thread_id for item in _threads(client, row)):
        raise HTTPException(status_code=404, detail="Conversation not found")
    append_record(client, session_id, user.id, "chat", {"id": str(thread_id), "deleted": True})
    return {"deleted": True}


@router.post("/{session_id}/chats/{thread_id}/messages", response_model=ChatThread)
async def send_message(session_id: uuid.UUID, thread_id: uuid.UUID, payload: MessageCreate, context=Depends(require_organisation), _csrf: None = Depends(require_csrf)):
    client = production_client()
    user, row = _session(client, session_id, context)
    thread = next((item for item in _threads(client, row) if item.id == thread_id), None)
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Type a message first")
    thread.messages.append(ChatMessage(role="user", content=content))
    if not any(item.role == "assistant" for item in thread.messages) and thread.title == "New conversation":
        thread.title = content[:60] + ("…" if len(content) > 60 else "")
    try:
        text = await chat.reply(payload.model, session_detail(client, row).transcript, [{"role": item.role, "content": item.content} for item in thread.messages if not item.error])
        thread.messages.append(ChatMessage(role="assistant", content=text, model=payload.model))
    except chat.ChatError as exc:
        thread.messages.append(ChatMessage(role="assistant", content=str(exc), model=payload.model, error=True))
    thread.updated_at = datetime.utcnow()
    append_record(client, session_id, user.id, "chat", thread.model_dump(mode="json"))
    return thread
