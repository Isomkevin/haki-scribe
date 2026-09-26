"""Small, dependency-free usage ledger for the workspace cost dashboard."""

from __future__ import annotations

import json
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_events: deque[dict[str, Any]] = deque(maxlen=2_000)
_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "openrouter_usage_seed.json"


def _load_seed() -> list[dict[str, Any]]:
    try:
        payload = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
        return [item for item in payload.get("events", []) if isinstance(item, dict)]
    except (OSError, ValueError, TypeError):
        return []


_seed_events = _load_seed()


def record(*, task: str, model: str, provider: str, prompt: str, response: str | None, usage: dict | None = None) -> None:
    usage = usage or {}
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or max(1, len(prompt) // 4))
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or max(0, len(response or "") // 4))
    _events.append({
        "at": datetime.now(timezone.utc).isoformat(), "task": task, "model": model, "provider": provider, "requests": 1,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "cost_usd": float(usage.get("cost") or usage.get("cost_total") or 0), "estimated": not bool(usage), "historical": False,
    })


def dashboard() -> dict[str, Any]:
    events = [*_seed_events, *_events]
    by_task: dict[str, dict[str, int]] = {}
    for task, items in _group(events, "task").items():
        by_task[task] = _totals(items)
    return {
        "window": "imported OpenRouter history plus this backend process",
        **_totals(events),
        "by_task": by_task,
        "models": dict(Counter({model: sum(int(item.get("requests", 1)) for item in events if item["model"] == model) for model in {item["model"] for item in events}})),
        "estimated_requests": sum(int(item.get("requests", 1)) for item in events if item["estimated"]),
        "historical_requests": sum(int(item.get("requests", 1)) for item in events if item.get("historical")),
    }


def _group(items: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(str(item[key]), []).append(item)
    return grouped


def _totals(items: list[dict]) -> dict[str, int]:
    prompt = sum(item["prompt_tokens"] for item in items)
    completion = sum(item["completion_tokens"] for item in items)
    return {
        "requests": sum(int(item.get("requests", 1)) for item in items),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "cost_usd": round(sum(float(item.get("cost_usd") or 0) for item in items), 6),
    }
