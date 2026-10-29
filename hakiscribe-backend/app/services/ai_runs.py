"""Metadata-only AI run ledger — never stores transcript or privileged text.

Demo mode keeps an in-process deque. Production can also persist rows via the
``ai_runs`` migration when a DATABASE_URL / Supabase project is configured.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

_runs: deque[dict[str, Any]] = deque(maxlen=2_000)


def record(
    *,
    task: str,
    provider: str,
    model_id: str,
    latency_ms: int,
    status: str = "ok",
    privileged_lines_excluded: int = 0,
    session_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Append one model-call row. No prompt, response, or transcript text."""
    row = {
        "id": len(_runs) + 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": str(session_id) if session_id else None,
        "task": task,
        "provider": provider,
        "model_id": model_id,
        "latency_ms": int(latency_ms),
        "status": status,
        "privileged_lines_excluded": int(privileged_lines_excluded),
    }
    # Defence: refuse accidental content fields.
    for forbidden in ("prompt", "response", "transcript", "text", "content"):
        row.pop(forbidden, None)
    _runs.append(row)
    return dict(row)


def recent(limit: int = 20) -> list[dict[str, Any]]:
    items = list(_runs)
    return [dict(r) for r in items[-limit:]]


def last_for_provider(provider: str = "nebius") -> Optional[dict[str, Any]]:
    for row in reversed(_runs):
        if row.get("provider") == provider:
            return dict(row)
    return None


def clear() -> None:
    _runs.clear()


def assert_no_marker(marker: str) -> None:
    """Raise if a privileged marker string leaked into any stored field."""
    needle = marker.lower()
    for row in _runs:
        blob = " ".join(str(v) for v in row.values()).lower()
        if needle in blob:
            raise AssertionError(f"Privileged marker found in ai_runs row: {row}")
