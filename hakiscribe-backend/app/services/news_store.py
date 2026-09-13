"""Persisted legal-intelligence monitors and hits. Separate from the
session store so a monitor webhook can write without reloading the library."""

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
    return upsert_monitor(record)


def upsert_monitor(record: dict[str, Any]) -> dict[str, Any]:
    monitor_id = record.get("id")
    topic = (record.get("topic") or "").strip().lower()
    for index, item in enumerate(_monitors):
        same_id = bool(monitor_id) and item.get("id") == monitor_id
        same_topic = bool(topic) and (item.get("topic") or "").strip().lower() == topic
        if same_id or same_topic:
            merged = {**item, **{key: value for key, value in record.items() if value is not None}}
            _monitors[index] = merged
            _persist()
            return merged
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


def add_hits(
    hits: list[dict[str, Any]],
    *,
    monitor_id: str | None,
    topic: str,
    session_id: str | None = None,
    matter_id: str | None = None,
    matter_name: str | None = None,
) -> list[dict[str, Any]]:
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
            "citation": hit.get("citation"),
            "kind": hit.get("kind"),
            "connection": hit.get("connection") or [],
            "relevance": hit.get("relevance"),
            "session_id": hit.get("session_id") or session_id,
            "matter_id": hit.get("matter_id") or matter_id,
            "matter_name": hit.get("matter_name") or matter_name,
            "received_at": datetime.utcnow().isoformat() + "Z",
        }
        _hits.append(record)
        existing.add(key)
        stored.append(record)
    if stored:
        _persist()
    return stored


def _connected(item: dict[str, Any]) -> bool:
    if not (item.get("session_id") or item.get("matter_id") or item.get("connection")):
        return False
    reasons = " ".join(item.get("connection") or []).lower()
    legal_marks = (
        "matter:",
        "party:",
        "authority:",
        "on the record:",
        "connected terms:",
        "arbitration",
        "contract",
        "defective",
        "statute",
        "clause",
        "section",
        "works",
        "contractor",
        "demand",
    )
    return any(mark in reasons for mark in legal_marks)


def list_hits(limit: int = 40, session_id: str | None = None, matter_id: str | None = None) -> list[dict[str, Any]]:
    items = [item for item in _hits if _connected(item)]
    if session_id:
        items = [item for item in items if item.get("session_id") == session_id]
    if matter_id:
        items = [item for item in items if item.get("matter_id") == matter_id]
    return list(reversed(items[-limit:]))


_load()
