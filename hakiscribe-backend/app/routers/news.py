"""Exa legal search and intelligence, grounded in matters and transcripts."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.integrations import exa_client
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


def _run_id(data: dict, payload: dict) -> Optional[str]:
    for candidate in (data.get("id"), data.get("runId"), payload.get("runId")):
        value = str(candidate or "")
        if value.startswith("run_"):
            return value
    event_like = str(data.get("id") or "")
    if event_like and not event_like.startswith("event_"):
        return event_like
    return None


@webhook_router.post("/exa")
async def receive_exa_monitor(request: Request):
    """Exa Monitors delivery. The webhook is a run envelope — fetch output.results."""
    payload = await request.json()
    if not isinstance(payload, dict):
        return {"received": 0}

    event_type = str(payload.get("type") or "")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    if event_type and event_type not in ("monitor.run.completed",):
        return {"received": 0, "ignored": event_type}

    status = data.get("status")
    if status and status != "completed":
        return {"received": 0, "status": status}

    monitor_id = (
        data.get("monitorId")
        or data.get("monitor_id")
        or payload.get("monitorId")
        or payload.get("monitor_id")
    )
    run_id = _run_id(data, payload)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    monitor = news_store.get_monitor(str(monitor_id)) if monitor_id else None
    topic = (
        (monitor or {}).get("topic")
        or metadata.get("matter_name")
        or payload.get("name")
        or "legal-intelligence"
    )

    results: list[dict] = []
    output = data.get("output") if isinstance(data.get("output"), dict) else {}
    for candidate in (payload.get("results"), data.get("results"), output.get("results")):
        if isinstance(candidate, list) and candidate:
            results = [item for item in candidate if isinstance(item, dict)]
            break

    if not results and monitor_id and run_id:
        run = await exa_client.get_run(str(monitor_id), str(run_id))
        if run is None:
            raise HTTPException(status_code=503, detail="Could not load monitor run from Exa")
        results = legal_intel.results_from_run(run)

    stored = legal_intel.ingest_monitor_results(
        results,
        monitor=monitor,
        monitor_id=str(monitor_id) if monitor_id else None,
        topic=str(topic),
        metadata=metadata,
    )
    return {"received": len(stored), "monitor_id": monitor_id, "run_id": run_id}
