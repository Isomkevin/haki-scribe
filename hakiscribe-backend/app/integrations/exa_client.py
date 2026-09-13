"""Exa retrieval — legal search, citation crawl, and matter-grounded intelligence.

Request shapes follow the official build-with-exa skill:
https://exa.ai/docs/reference/search

- /search is the default. Recommended body is query + type auto +
  contents.highlights only.
- /contents crawls URLs we already have (citations spoken or found).
- /monitors schedules recurring legal-development search and posts to our webhook.
- Company lookup keeps category=company because that surface retrieves
  raw company documents, not a people/company list-build.

No-ops to empty results when EXA_API_KEY is unset.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.exa.ai/search"
CONTENTS_URL = "https://api.exa.ai/contents"
MONITORS_URL = "https://api.exa.ai/monitors"

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)

CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation": {"type": "string"},
                    "kind": {"type": "string"},
                    "relevance": {"type": "string"},
                },
                "required": ["citation", "kind", "relevance"],
            },
        }
    },
    "required": ["citations"],
}

LEGAL_SYSTEM_PROMPT = (
    "Prefer Kenya Law, the Kenya Gazette, the Judiciary, and reported Kenyan cases. "
    "Drop pages that do not name a statute, section, case, or gazette notice. "
    "Never invent a citation; omit a field when it cannot be verified on the page."
)

NEWS_SYSTEM_PROMPT = (
    "Prefer recent reporting from identifiable publications. "
    "Drop undated press-release copies that add no facts. "
    "Never invent a publication date."
)

DEVELOPMENT_SYSTEM_PROMPT = (
    "Prefer Kenya Law, the Kenya Gazette, Judiciary notices, and reporting that "
    "names a statute, section, case, or gazette notice. "
    "Drop general commercial news that is not a legal development. "
    "Never invent a citation or publication date."
)


def _api_key() -> Optional[str]:
    return os.environ.get("EXA_API_KEY") or None


def is_configured() -> bool:
    return bool(_api_key())


_last_error: str | None = None


def last_error() -> str | None:
    return _last_error


def _headers() -> dict[str, str]:
    key = _api_key() or ""
    return {
        "x-api-key": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _highlight(item: dict[str, Any]) -> Optional[str]:
    highlights = item.get("highlights") or []
    if highlights:
        return str(highlights[0]).strip() or None
    text = (item.get("text") or "").strip()
    return text or None


def _normalise(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in results:
        url = item.get("url")
        if not url:
            continue
        out.append(
            {
                "title": item.get("title") or url,
                "url": url,
                "published": item.get("publishedDate"),
                "extract": _highlight(item),
                "citation": None,
                "kind": None,
            }
        )
    return out


async def _request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 45,
) -> Optional[dict[str, Any]]:
    global _last_error
    if not _api_key():
        _last_error = "EXA_API_KEY is not set"
        return None
    _last_error = None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method,
                url,
                headers=_headers(),
                json=payload if payload is not None else None,
            )
            if resp.status_code >= 400:
                _last_error = f"{method} {url} -> {resp.status_code}: {resp.text[:400]}"
                logger.warning("Exa %s", _last_error)
                return None
            data = resp.json() if resp.content else {}
            return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 — retrieval is best-effort
        _last_error = f"{method} {url} failed ({exc})"
        logger.warning("Exa %s", _last_error)
        return None


async def _post(url: str, payload: dict[str, Any], timeout: float = 45) -> Optional[dict[str, Any]]:
    return await _request("POST", url, payload, timeout=timeout)


async def _get(url: str, timeout: float = 30) -> Optional[dict[str, Any]]:
    return await _request("GET", url, timeout=timeout)


async def search_web(query: str) -> list[dict[str, Any]]:
    """Recommended /search request: query + auto + highlights."""
    data = await _post(
        SEARCH_URL,
        {
            "query": query,
            "type": "auto",
            "contents": {"highlights": True},
        },
    )
    return _normalise((data or {}).get("results", []))


async def search_legal(query: str) -> list[dict[str, Any]]:
    """Alias kept for older call sites."""
    return await search_citations(query)


async def search_citations(query: str) -> list[dict[str, Any]]:
    """Citation retrieval. Source preference lives in systemPrompt, not a domain allowlist."""
    data = await _post(
        SEARCH_URL,
        {
            "query": f"{query} Kenyan law authorities",
            "type": "auto",
            "contents": {"highlights": True},
            "systemPrompt": LEGAL_SYSTEM_PROMPT,
            "outputSchema": CITATION_SCHEMA,
        },
    )
    if not data:
        return []
    sources = _normalise(data.get("results", []))
    citations = ((data.get("output") or {}).get("content") or {}).get("citations") or []
    for index, citation in enumerate(citations):
        if index < len(sources) and isinstance(citation, dict):
            sources[index]["citation"] = citation.get("citation")
            sources[index]["kind"] = citation.get("kind")
            if citation.get("relevance") and not sources[index]["extract"]:
                sources[index]["extract"] = citation.get("relevance")
    return sources


async def search_news(query: str) -> list[dict[str, Any]]:
    """Kept for older call sites. Prefer search_legal_developments."""
    return await search_legal_developments(query)


async def search_legal_developments(query: str) -> list[dict[str, Any]]:
    """Legal developments related to a grounded matter query — not general news."""
    data = await _post(
        SEARCH_URL,
        {
            "query": f"latest Kenyan legal developments {query}",
            "type": "auto",
            "contents": {"highlights": True},
            "systemPrompt": DEVELOPMENT_SYSTEM_PROMPT,
        },
    )
    return _normalise((data or {}).get("results", []))


async def search_company(name: str) -> Optional[dict[str, Any]]:
    """Raw company document lookup — the documented use of category=company."""
    if not name:
        return None
    data = await _post(
        SEARCH_URL,
        {
            "query": name,
            "type": "auto",
            "category": "company",
            "contents": {"highlights": True},
        },
    )
    results = _normalise((data or {}).get("results", []))
    if not results:
        return None
    top = results[0]
    return {
        "title": top.get("title"),
        "url": top.get("url"),
        "highlight": top.get("extract"),
        "published": top.get("published"),
        "extract": top.get("extract"),
    }


async def crawl_urls(urls: list[str]) -> list[dict[str, Any]]:
    """/contents — known-URL citation crawl. Highlights are top-level here."""
    cleaned = []
    seen: set[str] = set()
    for url in urls:
        href = url.rstrip(".,;\"'")
        if href and href not in seen:
            seen.add(href)
            cleaned.append(href)
    if not cleaned:
        return []
    data = await _post(CONTENTS_URL, {"urls": cleaned[:8], "highlights": True})
    if not data:
        return []
    failed = {
        item.get("id")
        for item in data.get("statuses") or []
        if item.get("status") == "error"
    }
    return [item for item in _normalise(data.get("results", [])) if item.get("url") not in failed]


def urls_from_text(text: str) -> list[str]:
    return [match.rstrip(".,;\"'") for match in URL_RE.findall(text or "")]


async def create_monitor(
    name: str,
    query: str,
    webhook_url: str,
    period: str = "1d",
    legal: bool = True,
    metadata: dict[str, str] | None = None,
) -> Optional[dict[str, Any]]:
    """Standalone Monitors API. Store webhookSecret immediately — it cannot be fetched later."""
    search_query = f"latest Kenyan legal developments {query}" if legal else f"latest news {query}"
    body: dict[str, Any] = {
        "name": name,
        "search": {
            "query": search_query,
            "contents": {"highlights": True},
        },
        "trigger": {"type": "interval", "period": period},
        "webhook": {
            "url": webhook_url,
            "events": ["monitor.run.completed"],
        },
    }
    if metadata:
        body["metadata"] = {key: value for key, value in metadata.items() if value}
    return await _post(MONITORS_URL, body, timeout=30)


async def trigger_monitor(monitor_id: str) -> Optional[dict[str, Any]]:
    return await _post(f"{MONITORS_URL}/{monitor_id}/trigger", {}, timeout=30)


async def get_run(monitor_id: str, run_id: str) -> Optional[dict[str, Any]]:
    return await _get(f"{MONITORS_URL}/{monitor_id}/runs/{run_id}")


async def wait_for_latest_run(
    monitor_id: str,
    attempts: int = 4,
    delay: float = 2.0,
) -> Optional[dict[str, Any]]:
    """Poll until the newest run completes or fails. Webhook is still the durable path."""
    latest: dict[str, Any] | None = None
    for _ in range(max(1, attempts)):
        listing = await _get(f"{MONITORS_URL}/{monitor_id}/runs")
        runs = (listing or {}).get("data") or []
        if runs and isinstance(runs[0], dict):
            latest = runs[0]
            status = latest.get("status")
            run_id = latest.get("id")
            if status == "completed" and run_id:
                return await get_run(monitor_id, str(run_id)) or latest
            if status == "failed":
                return latest
        await asyncio.sleep(delay)
    return latest
