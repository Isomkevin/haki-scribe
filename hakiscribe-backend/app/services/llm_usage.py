"""Small, dependency-free usage ledger for the workspace cost dashboard."""

from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any

_events: deque[dict[str, Any]] = deque(maxlen=2_000)


def record(*, task: str, model: str, provider: str, prompt: str, response: str | None, usage: dict | None = None) -> None:
    usage = usage or {}
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or max(1, len(prompt) // 4))
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or max(0, len(response or "") // 4))
    _events.append({
        "at": datetime.now(timezone.utc).isoformat(), "task": task, "model": model, "provider": provider,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "estimated": not bool(usage),
    })


def dashboard() -> dict[str, Any]:
    events = list(_events)
    by_task: dict[str, dict[str, int]] = {}
    for task, items in _group(events, "task").items():
        by_task[task] = _totals(items)
    return {
        "window": "since this backend process started",
        "requests": len(events),
        **_totals(events),
        "by_task": by_task,
        "models": dict(Counter(item["model"] for item in events)),  # actual router-selected model when returned
        "estimated_requests": sum(1 for item in events if item["estimated"]),
    }


def _group(items: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(str(item[key]), []).append(item)
    return grouped


def _totals(items: list[dict]) -> dict[str, int]:
    prompt = sum(item["prompt_tokens"] for item in items)
    completion = sum(item["completion_tokens"] for item in items)
    return {"requests": len(items), "prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}
