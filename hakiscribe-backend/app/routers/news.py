"""Exa legal search and intelligence, grounded in matters and transcripts."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from app.services import legal_intel, news_store

router = APIRouter()
webhook_router = APIRouter()


class NewsSearchRequest(BaseModel):
    query: Optional[str] = None
    session_id: Optional[str] = None
    matter_id: Optional[str] = None


class NewsWatchRequest(BaseModel):
    topic: Optional[str] = None
    session_id: Optional[str] = None
    matter_id: Optional[str] = None
    period: str = "1d"


@router.post("/search")
async def search_news(payload: NewsSearchRequest):
    return await legal_intel.retrieve(
        session_id=payload.session_id,
        matter_id=payload.matter_id,
        extra_query=payload.query,
    )


@router.get("/hits")
def list_hits(session_id: Optional[str] = Query(default=None), matter_id: Optional[str] = Query(default=None)):
    return {
        "hits": news_store.list_hits(session_id=session_id, matter_id=matter_id),
        "monitors": news_store.list_monitors(),
    }


@router.post("/watch")
async def watch_news(payload: NewsWatchRequest):
    return await legal_intel.watch(
        session_id=payload.session_id,
        matter_id=payload.matter_id,
        period=payload.period,
    )


@webhook_router.post("/exa")
async def receive_exa_monitor(payload: dict, x_exa_signature: str = Header(default="")):
    """Exa Monitors delivery. Hits are stored only when they still connect to the matter."""
    del x_exa_signature
    results = payload.get("results") or payload.get("data") or []
    if isinstance(results, dict):
        results = results.get("results") or []
    topic = (
        payload.get("name")
        or (payload.get("search") or {}).get("query")
        or payload.get("query")
        or "legal-intelligence"
    )
    monitor_id = payload.get("id") or payload.get("monitorId") or payload.get("monitor_id")
    monitor = news_store.get_monitor(str(monitor_id)) if monitor_id else news_store.find_monitor_by_topic(str(topic))
    scope = legal_intel.resolve_scope(
        session_id=(monitor or {}).get("session_id"),
        matter_id=(monitor or {}).get("matter_id"),
    )
    normalised = []
    for item in results:
        if not isinstance(item, dict):
            continue
        highlights = item.get("highlights") or []
        raw = {
            "title": item.get("title"),
            "url": item.get("url"),
            "published": item.get("publishedDate") or item.get("published"),
            "extract": (highlights[0] if highlights else item.get("text") or item.get("extract")),
        }
        scored = legal_intel.score_hit(raw, scope) if scope else None
        if scored:
            normalised.append(scored)
    stored = news_store.add_hits(
        normalised,
        monitor_id=str(monitor_id) if monitor_id else None,
        topic=str(topic),
        session_id=(monitor or {}).get("session_id"),
        matter_id=(monitor or {}).get("matter_id"),
        matter_name=(scope or {}).get("matter_name"),
    )
    return {"received": len(stored)}
