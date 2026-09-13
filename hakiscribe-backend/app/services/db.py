"""
Durable Postgres persistence for the HakiScribe store.

Set DATABASE_URL (any Postgres: Supabase, Neon, Render Postgres) and every
session, transcript, flag, detected action and generated document survives a
process restart, a redeploy, or a free-instance sleep. Leave it unset and the
store falls back to the JSON snapshot file exactly as before — nothing else in
the codebase has to know which mode is active.

The schema is deliberately one generic table: HakiScribe's records are already
Pydantic models serialised to JSON, so a typed column-per-field schema would
only duplicate the models and drift from them. Row counts here are small
(one row per session/matter/contact), so a whole-snapshot rewrite inside one
transaction is both simple and safe.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS haki_records (
    kind text NOT NULL,
    id text NOT NULL,
    data jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, id)
);
CREATE INDEX IF NOT EXISTS haki_records_kind_idx ON haki_records (kind);
"""

# kind -> how the snapshot payload stores it.
_LIST_KEYS = ("sessions", "matters", "contacts")  # list of objects with an "id"
_MAP_KEYS = ("transcripts", "actions", "flags", "results")  # session_id -> list
_LINK_KEYS = ("session_matter_ids", "session_contact_ids")  # session_id -> ids

_state: dict[str, Any] = {"checked": False, "ok": False}


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    # Supabase/Heroku hand out postgres:// which psycopg no longer accepts.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def _connect():
    import psycopg  # imported lazily so the app runs without the driver installed

    return psycopg.connect(database_url(), autocommit=False, connect_timeout=10)


def enabled() -> bool:
    """True once we've confirmed we can actually reach the database."""
    if _state["checked"]:
        return bool(_state["ok"])
    _state["checked"] = True
    if not database_url():
        _state["ok"] = False
        return False
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_DDL)
            conn.commit()
        _state["ok"] = True
        logger.info("HakiScribe is persisting to Postgres")
    except Exception as exc:  # noqa: BLE001 — never let persistence break the API
        _state["ok"] = False
        logger.warning("Postgres unavailable, falling back to the file store: %s", exc)
    return bool(_state["ok"])


def _rows(payload: dict) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for key in _LIST_KEYS:
        for item in payload.get(key, []):
            rows.append((key, str(item.get("id")), json.dumps(item, default=str)))
    for key in _MAP_KEYS:
        for session_id, items in payload.get(key, {}).items():
            rows.append((key, str(session_id), json.dumps(items, default=str)))
    for key in _LINK_KEYS:
        for session_id, ids in payload.get(key, {}).items():
            rows.append((key, str(session_id), json.dumps(ids, default=str)))
    return rows


def save_snapshot(payload: dict) -> bool:
    if not enabled():
        return False
    rows = _rows(payload)
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM haki_records")
                if rows:
                    cur.executemany(
                        "INSERT INTO haki_records (kind, id, data) VALUES (%s, %s, %s::jsonb)",
                        rows,
                    )
            conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save the HakiScribe snapshot to Postgres: %s", exc)
        return False


def load_snapshot() -> Optional[dict]:
    """Rebuild the snapshot payload from Postgres, or None when unavailable/empty."""
    if not enabled():
        return None
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT kind, id, data FROM haki_records")
                records = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read the HakiScribe snapshot from Postgres: %s", exc)
        return None
    if not records:
        return None
    payload: dict[str, Any] = {key: [] for key in _LIST_KEYS}
    for key in (*_MAP_KEYS, *_LINK_KEYS):
        payload[key] = {}
    for kind, record_id, data in records:
        value = json.loads(data) if isinstance(data, (str, bytes)) else data
        if kind in _LIST_KEYS:
            payload[kind].append(value)
        elif kind in payload:
            payload[kind][record_id] = value
    return payload


def status() -> dict:
    return {"configured": bool(database_url()), "connected": enabled()}
