"""
Optional enrichment step: when a detected action names a company or
counterparty, look it up via Exa's company-search category to attach a
short, clearly-labeled 'background info' blurb — never used to add
claims into the drafted legal text itself, only as a sanity-check
reference the user sees alongside the card.

No-ops (returns None) if EXA_API_KEY isn't set.
"""

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.exa.ai/search"


def _api_key() -> Optional[str]:
    return os.environ.get("EXA_API_KEY") or None


async def search_company(name: str) -> Optional[dict[str, Any]]:
    if not _api_key() or not name:
        return None
    results = await _search(
        {"query": name, "category": "company", "numResults": 1, "contents": {"highlights": True}}
    )
    if not results:
        return None
    top = results[0]
    return {"title": top.get("title"), "url": top.get("url"), "highlight": top.get("extract")}


async def _search(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Never raise into an action card — an unreachable or rejected search
    degrades to 'no sources retrieved', which the executor reports honestly."""
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                SEARCH_URL,
                headers={"x-api-key": _api_key(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return _normalise(resp.json().get("results", []))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Exa search failed (%s); continuing without sources", exc)
        return []


def _normalise(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in results:
        highlights = item.get("highlights") or []
        text = (item.get("text") or "").strip()
        out.append(
            {
                "title": item.get("title") or item.get("url"),
                "url": item.get("url"),
                "published": item.get("publishedDate"),
                "extract": (highlights[0] if highlights else text[:600]) or None,
            }
        )
    return out


async def search_legal(query: str, num_results: int = 6) -> list[dict[str, Any]]:
    """Retrieval for a legal research card — biased toward Kenyan primary
    sources (Kenya Law, the National Council for Law Reporting, the
    Judiciary, the Kenya Gazette) plus reputable commentary. Returns [] if
    Exa isn't configured, which the executor reports honestly."""
    if not _api_key() or not query.strip():
        return []
    payload = {
        "query": f"{query} (Kenya law)",
        "type": "auto",
        "numResults": num_results,
        "includeDomains": [
            "kenyalaw.org",
            "new.kenyalaw.org",
            "judiciary.go.ke",
            "kenyalawreports.or.ke",
            "parliament.go.ke",
            "gazettes.africa",
        ],
        "contents": {"highlights": True, "text": {"maxCharacters": 1200}},
    }
    results = await _search(payload)
    if results:
        return results
    # Kenyan primary sources can come back empty for a narrow question;
    # retry once unrestricted rather than reporting "no authorities".
    payload.pop("includeDomains", None)
    return await _search(payload)


async def search_web(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    """Open web lookup for a background/due-diligence card. Clearly labelled
    as background only — never folded into drafted legal text."""
    if not _api_key() or not query.strip():
        return []
    return await _search(
        {
            "query": query,
            "type": "auto",
            "numResults": num_results,
            "contents": {"highlights": True, "text": {"maxCharacters": 800}},
        }
    )
