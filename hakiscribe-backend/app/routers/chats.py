"""Threaded chats about a session, saved with the session record."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import ChatMessage, ChatThread
from app.services import chat, storage

router = APIRouter()


class ThreadCreate(BaseModel):
    title: Optional[str] = None


class MessageCreate(BaseModel):
    content: str
    model: Optional[str] = None


def _require_session(session_id: uuid.UUID):
    detail = storage.get_session(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail


def _require_thread(session_id: uuid.UUID, thread_id: uuid.UUID) -> ChatThread:
    thread = storage.get_chat(session_id, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


@router.get("/{session_id}/chats", response_model=list[ChatThread])
def list_threads(session_id: uuid.UUID):
    _require_session(session_id)
    return storage.list_chats(session_id)


@router.post("/{session_id}/chats", response_model=ChatThread)
def create_thread(session_id: uuid.UUID, payload: ThreadCreate):
    _require_session(session_id)
    thread = ChatThread(session_id=session_id, title=(payload.title or "New conversation").strip()[:80])
    return storage.save_chat(thread)


@router.get("/{session_id}/chats/{thread_id}", response_model=ChatThread)
def get_thread(session_id: uuid.UUID, thread_id: uuid.UUID):
    _require_session(session_id)
    return _require_thread(session_id, thread_id)


@router.delete("/{session_id}/chats/{thread_id}")
def delete_thread(session_id: uuid.UUID, thread_id: uuid.UUID):
    _require_session(session_id)
    if not storage.delete_chat(session_id, thread_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@router.post("/{session_id}/chats/{thread_id}/messages", response_model=ChatThread)
async def send_message(session_id: uuid.UUID, thread_id: uuid.UUID, payload: MessageCreate):
    detail = _require_session(session_id)
    thread = _require_thread(session_id, thread_id)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Type a message first")

    thread.messages.append(ChatMessage(role="user", content=content))
    if not any(m.role == "assistant" for m in thread.messages) and thread.title == "New conversation":
        thread.title = content[:60] + ("…" if len(content) > 60 else "")
    thread.updated_at = datetime.utcnow()
    storage.save_chat(thread)

    history = [{"role": m.role, "content": m.content} for m in thread.messages if not m.error]
    try:
        text = await chat.reply(payload.model, detail.transcript, history)
        thread.messages.append(ChatMessage(role="assistant", content=text, model=payload.model))
    except chat.ChatError as exc:
        thread.messages.append(ChatMessage(role="assistant", content=str(exc), model=payload.model, error=True))
    except Exception as exc:  # noqa: BLE001 — keep the thread usable
        thread.messages.append(
            ChatMessage(role="assistant", content=f"The model could not be reached: {exc}", model=payload.model, error=True)
        )
    thread.updated_at = datetime.utcnow()
    return storage.save_chat(thread)
