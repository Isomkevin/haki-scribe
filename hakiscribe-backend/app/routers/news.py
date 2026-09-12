"""Exa news monitoring: one-shot search plus scheduled monitors."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.integrations import exa_client
from app.services import news_store

router = APIRouter()
webhook_router = APIRouter()


class NewsSearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class NewsWatchRequest(BaseModel):
    topic: str
    session_id: Optional[str] = None
    period: str = "1d"


def _webhook_url() -> Optional[str]:
    configured = os.environ.get("EXA_MONITOR_WEBHOOK_URL", "").strip()
    if configured:
        return configured
    base = (os.environ.get("BACKEND_INTERNAL_URL") or "").rstrip("/")
    return f"{base}/webhooks/exa" if base.startswith("http") else None


@router.post("/search")
async def search_news(payload: NewsSearchRequest):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="A news query is required.")
    hits = await exa_client.search_news(payload.query.strip())
    stored = news_store.add_hits(hits, monitor_id=None, topic=payload.query.strip())
    return {"query": payload.query.strip(), "hits": stored or hits, "configured": exa_client.is_configured()}


@router.get("/hits")
def list_hits():
    return {"hits": news_store.list_hits(), "monitors": news_store.list_monitors()}


@router.post("/watch")
async def watch_news(payload: NewsWatchRequest):
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="A topic is required.")

    existing = news_store.find_monitor_by_topic(topic)
    hits = await exa_client.search_news(topic)
    stored_hits = news_store.add_hits(hits, monitor_id=(existing or {}).get("id"), topic=topic)

    if existing:
        if existing.get("id"):
            await exa_client.trigger_monitor(existing["id"])
        return {"monitor": existing, "hits": stored_hits or hits, "created": False}

    webhook = _webhook_url()
    remote = None
    if webhook and exa_client.is_configured():
        remote = await exa_client.create_monitor(
            name=f"HakiScribe · {topic[:60]}",
            query=topic,
            webhook_url=webhook,
            period=payload.period,
        )

    record = {
        "id": (remote or {}).get("id"),
        "topic": topic,
        "session_id": payload.session_id,
        "period": payload.period,
        "webhook_url": webhook,
        "webhook_secret": (remote or {}).get("webhookSecret") or (remote or {}).get("webhook_secret"),
        "status": "active" if remote else "local-only",
    }
    news_store.add_monitor(record)
    return {"monitor": {**record, "webhook_secret": None}, "hits": stored_hits or hits, "created": True}


@webhook_router.post("/exa")
async def receive_exa_monitor(payload: dict, x_exa_signature: str = Header(default="")):
    """Exa Monitors delivery. Hits are stored even if signature headers vary."""
    del x_exa_signature
    results = payload.get("results") or payload.get("data") or []
    if isinstance(results, dict):
        results = results.get("results") or []
    topic = (
        payload.get("name")
        or (payload.get("search") or {}).get("query")
        or payload.get("query")
        or "news"
    )
    monitor_id = payload.get("id") or payload.get("monitorId") or payload.get("monitor_id")
    normalised = []
    for item in results:
        if not isinstance(item, dict):
            continue
        highlights = item.get("highlights") or []
        normalised.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "published": item.get("publishedDate") or item.get("published"),
                "extract": (highlights[0] if highlights else item.get("text") or item.get("extract")),
            }
        )
    stored = news_store.add_hits(normalised, monitor_id=str(monitor_id) if monitor_id else None, topic=str(topic))
    return {"received": len(stored)}
