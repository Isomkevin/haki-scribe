"""In-memory stand-in for the supabase-py query builder used by the production repos.

Supports the calls the backend makes: select / insert (row or list) / upsert /
update / delete, filtered by eq / in_ / lt, with order and limit. An UPDATE
applies its filters and its write in one step, like a single Postgres UPDATE,
so conditional claims behave as they would against the database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable
from uuid import uuid4


def _cmp_value(v: Any) -> Any:
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return v
    return v


class FakeQuery:
    def __init__(self, db: "FakeSupabase", name: str):
        self.db = db
        self.name = name
        self.op = "select"
        self.payload: Any = None
        self.filters: list[Callable[[dict[str, Any]], bool]] = []
        self.order_key: tuple[str, bool] | None = None
        self.limit_n: int | None = None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload):
        self.op, self.payload = "upsert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, key, value):
        self.filters.append(lambda r: str(r.get(key)) == str(value) if value is not None else r.get(key) is None)
        return self

    def in_(self, key, values):
        wanted = {str(v) for v in values}
        self.filters.append(lambda r: str(r.get(key)) in wanted)
        return self

    def lt(self, key, value):
        self.filters.append(lambda r: r.get(key) is not None and _cmp_value(r.get(key)) < _cmp_value(value))
        return self

    def order(self, key, desc=False):
        self.order_key = (key, desc)
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def _match(self, row):
        return all(f(row) for f in self.filters)

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self.op == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for item in items:
                row = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **item}
                self.db.check_unique(self.name, row)
                rows.append(row)
                out.append(dict(row))
            return SimpleNamespace(data=out)
        if self.op == "upsert":
            row = dict(self.payload)
            for existing in rows:
                if str(existing.get("id")) == str(row.get("id")):
                    existing.update(row)
                    return SimpleNamespace(data=[dict(existing)])
            row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            rows.append(row)
            return SimpleNamespace(data=[dict(row)])
        if self.op == "update":
            out = []
            for row in rows:
                if self._match(row):
                    row.update(self.payload)
                    out.append(dict(row))
            return SimpleNamespace(data=out)
        if self.op == "delete":
            keep = [r for r in rows if not self._match(r)]
            gone = [dict(r) for r in rows if self._match(r)]
            self.db.tables[self.name] = keep
            return SimpleNamespace(data=gone)
        out = [dict(r) for r in rows if self._match(r)]
        if self.order_key:
            key, desc = self.order_key
            out.sort(key=lambda r: str(r.get(key) or ""), reverse=desc)
        if self.limit_n is not None:
            out = out[: self.limit_n]
        return SimpleNamespace(data=out)


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    def check_unique(self, name: str, row: dict[str, Any]) -> None:
        # Mirrors haki_hearing_jobs_one_active (migration 004).
        if name == "haki_hearing_jobs" and row.get("status") in ("queued", "running"):
            for other in self.tables.get(name, []):
                if other["hearing_id"] == row["hearing_id"] and other["status"] in ("queued", "running"):
                    raise RuntimeError('23505 duplicate key value violates unique constraint "haki_hearing_jobs_one_active"')
