"""
Optional enrichment step: when a detected action names a company or
counterparty, look it up via Exa's company-search category to attach a
short, clearly-labeled 'background info' blurb — never used to add
claims into the drafted legal text itself, only as a sanity-check
reference the user sees alongside the card.

No-ops (returns None) if EXA_API_KEY isn't set.
"""

import os
from typing import Any, Optional

import httpx

SEARCH_URL = "https://api.exa.ai/search"


def _api_key() -> Optional[str]:
    return os.environ.get("EXA_API_KEY") or None


async def search_company(name: str) -> Optional[dict[str, Any]]:
    if not _api_key() or not name:
        return None
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            SEARCH_URL,
            headers={"x-api-key": _api_key(), "Content-Type": "application/json"},
            json={
                "query": name,
                "category": "company",
                "numResults": 1,
                "contents": {"highlights": True},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        top = results[0]
        return {
            "title": top.get("title"),
            "url": top.get("url"),
            "highlight": (top.get("highlights") or [None])[0],
        }
