"""Tavily web search — supporting legal research context only.

Tavily results are EXTERNAL AUTHORITIES, never transcript evidence and
never unverified drafted facts. Everything returned from here is labelled
"External authorities (not evidence)" in the UI.

Server-side only: the TAVILY_API_KEY lives in the connector store or the
workspace env and never reaches the browser.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.tavily.com/search"

# Kenyan legal domains, per the HakiScribe research spec.
KENYA_LEGAL_DOMAINS = [
    "kenyalaw.org",
    "new.kenyalaw.org",
    "judiciary.go.ke",
    "lawsociety.or.ke",
]


def creds() -> dict[str, Any]:
    from app.services import integrations
    return integrations.get_creds("tavily") or {}


def is_configured() -> bool:
    return bool(str(creds().get("api_key") or "").strip())


def _key(c: dict[str, Any] | None = None) -> str:
    c = c if c is not None else creds()
    return str(c.get("api_key") or "").strip() or os.environ.get("TAVILY_API_KEY", "").strip()


async def search(
    query: str,
    *,
    include_domains: list[str] | None = None,
    max_results: int = 8,
    timeout_s: float = 30.0,
    creds_override: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search Tavily with advanced depth; returns normalised hits.

    Each hit: {"title", "url", "content", "score", "published_date"}.
    Raises RuntimeError with a plain-language message on failure.
    """
    key = _key(creds_override)
    if not key:
        raise RuntimeError("Tavily is not connected. Add your Tavily API key on the connector card.")
    payload: dict[str, Any] = {
        "api_key": key,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
    }
    domains = include_domains if include_domains is not None else KENYA_LEGAL_DOMAINS
    if domains:
        payload["include_domains"] = domains
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(SEARCH_URL, json=payload)
    if resp.status_code in (401, 403):
        raise RuntimeError("Tavily rejected the API key. Re-check the key on the connector card.")
    if resp.status_code >= 400:
        raise RuntimeError(f"Tavily returned {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    hits: list[dict[str, Any]] = []
    for item in body.get("results") or []:
        if not isinstance(item, dict):
            continue
        hits.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "content": str(item.get("content") or "").strip(),
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )
    return hits


async def verify(creds_payload: dict[str, Any]) -> dict[str, Any]:
    """Credential probe for the connector verifier."""
    try:
        hits = await search("Kenya Evidence Act burden of proof", max_results=1, creds_override=creds_payload)
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    if not hits:
        return {"ok": True, "error": None, "detail": "Key accepted; no results for the probe query."}
    return {"ok": True, "error": None, "detail": f"Key accepted; probe returned {len(hits)} result(s)."}


def status() -> dict[str, Any]:
    return {
        "configured": is_configured(),
        "domains": KENYA_LEGAL_DOMAINS,
        "label": "External authorities (not evidence)",
    }
