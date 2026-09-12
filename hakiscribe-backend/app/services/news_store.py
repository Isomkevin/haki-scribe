"""Persisted Exa news monitors and hits. Separate from the session store
so a monitor webhook can write without reloading the whole library."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
_PATH = Path(os.environ.get("HAKISCRIBE_NEWS_STORE", "data/news.json"))

_monitors: list[dict[str, Any]] = []
_hits: list[dict[str, Any]] = []


def _persist() -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps({"monitors": _monitors, "hits": _hits[-200:]}, default=str), encoding="utf-8")
        tmp.replace(_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not persist news store: %s", exc)


def _load() -> None:
    if not _PATH.exists():
        return
    try:
        payload = json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load news store: %s", exc)
        return
    _monitors.extend(payload.get("monitors") or [])
    _hits.extend(payload.get("hits") or [])


def add_monitor(record: dict[str, Any]) -> dict[str, Any]:
    _monitors.append(record)
    _persist()
    return record


def list_monitors() -> list[dict[str, Any]]:
    return list(_monitors)


def get_monitor(monitor_id: str) -> Optional[dict[str, Any]]:
    return next((item for item in _monitors if item.get("id") == monitor_id), None)


def find_monitor_by_topic(topic: str) -> Optional[dict[str, Any]]:
    needle = topic.strip().lower()
    return next((item for item in _monitors if (item.get("topic") or "").strip().lower() == needle), None)


def add_hits(hits: list[dict[str, Any]], *, monitor_id: str | None, topic: str) -> list[dict[str, Any]]:
    stored = []
    existing = {(item.get("url"), item.get("title")) for item in _hits}
    for hit in hits:
        key = (hit.get("url"), hit.get("title"))
        if not hit.get("url") or key in existing:
            continue
        record = {
            "id": str(uuid.uuid4()),
            "monitor_id": monitor_id,
            "topic": topic,
            "title": hit.get("title"),
            "url": hit.get("url"),
            "published": hit.get("published"),
            "extract": hit.get("extract"),
            "received_at": datetime.utcnow().isoformat() + "Z",
        }
        _hits.append(record)
        existing.add(key)
        stored.append(record)
    if stored:
        _persist()
    return stored


def list_hits(limit: int = 40) -> list[dict[str, Any]]:
    return list(reversed(_hits[-limit:]))


_load()
