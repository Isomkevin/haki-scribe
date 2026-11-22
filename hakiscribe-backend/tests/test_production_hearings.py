"""ADR-012 (b) — org-scoped production hearings with mocked Supabase client."""

from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from app.models.schemas import HearingConfirmRequest, HearingCreate, HearingSource, HearingStatus
from app.services.production_hearings import ProductionHearingsRepo, resolve_zoom_organisation


class _FakeTable:
    def __init__(self, store: dict[str, list[dict[str, Any]]], name: str):
        self.store = store
        self.name = name
        self._filters: list[tuple[str, Any]] = []
        self._order = None
        self._limit = None
        self._payload: Any = None
        self._op = "select"
        self._select = "*"

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(self, payload):
        self._op = "upsert"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = list(self.store.setdefault(self.name, []))
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", datetime.utcnow().isoformat())
            row.setdefault("updated_at", datetime.utcnow().isoformat())
            rows.append(row)
            self.store[self.name] = rows
            return MagicMock(data=[row])
        if self._op == "upsert":
            row = dict(self._payload)
            rid = str(row.get("id"))
            replaced = False
            for i, existing in enumerate(rows):
                if str(existing.get("id")) == rid:
                    rows[i] = {**existing, **row}
                    row = rows[i]
                    replaced = True
                    break
            if not replaced:
                rows.append(row)
            self.store[self.name] = rows
            return MagicMock(data=[row])
        if self._op == "delete":
            kept = []
            for r in rows:
                if all(str(r.get(k)) == str(v) for k, v in self._filters):
                    continue
                kept.append(r)
            self.store[self.name] = kept
            return MagicMock(data=[])
        if self._op == "update":
            out = []
            for i, r in enumerate(rows):
                if all(str(r.get(k)) == str(v) for k, v in self._filters):
                    rows[i] = {**r, **self._payload}
                    out.append(rows[i])
            self.store[self.name] = rows
            return MagicMock(data=out)
        # select
        matched = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in self._filters)]
        if self._limit:
            matched = matched[: self._limit]
        return MagicMock(data=matched)


class _FakeClient:
    def __init__(self):
        self.store: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str):
        return _FakeTable(self.store, name)


class ProductionHearingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.org_a = uuid4()
        self.org_b = uuid4()
        self.client = _FakeClient()
        self.repo_a = ProductionHearingsRepo(self.client, self.org_a)
        self.repo_b = ProductionHearingsRepo(self.client, self.org_b)
        matter_id = uuid4()
        self.matter_id = matter_id
        self.client.store["haki_matters"] = [
            {
                "id": str(matter_id),
                "organisation_id": str(self.org_a),
                "client_name": "Acme",
                "matter_name": "E123 of 2024",
            }
        ]

    def test_org_isolation(self) -> None:
        hearing = self.repo_a.create(
            HearingCreate(source=HearingSource.manual_upload, title="Acme Holdings E123 of 2024")
        )
        listed_a = self.repo_a.list_hearings()
        listed_b = self.repo_b.list_hearings()
        self.assertEqual(len(listed_a), 1)
        self.assertEqual(len(listed_b), 0)
        with self.assertRaises(Exception):
            self.repo_b.get_hearing(hearing.id)

    def test_confirm_and_pipeline_metadata(self) -> None:
        hearing = self.repo_a.create(
            HearingCreate(source=HearingSource.manual_upload, title="Acme Holdings E123 of 2024")
        )
        self.repo_a.propose_matches(hearing.id)
        confirmed = self.repo_a.confirm_match(
            hearing.id,
            HearingConfirmRequest(decision="confirm", matter_id=self.matter_id),
            actor="tester@example.com",
        )
        self.assertEqual(confirmed.status, HearingStatus.matched)
        self.assertEqual(confirmed.matter_id, self.matter_id)
        updated = self.repo_a.set_pipeline_state(hearing.id, state="queued", job_id="run_123")
        self.assertEqual(updated.platform_metadata["pipeline"]["job_id"], "run_123")

    def test_zoom_org_map(self) -> None:
        org = uuid4()
        with patch.dict(
            "os.environ",
            {"ZOOM_HOST_ORG_MAP": f'{{"host-1": "{org}"}}', "ZOOM_DEFAULT_ORGANISATION_ID": ""},
            clear=False,
        ):
            self.assertEqual(resolve_zoom_organisation("host-1"), org)
            self.assertIsNone(resolve_zoom_organisation("unknown"))


class ProcessEnqueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_only_never_enqueues_trigger(self) -> None:
        from app.services import ai_mode, trigger_client

        ai_mode.clear_runtime_overrides()
        with patch.dict("os.environ", {"HAKISCRIBE_AI_MODE": "local_only", "TRIGGER_SECRET_KEY": "secret"}, clear=False):
            self.assertTrue(ai_mode.prefer_in_process_jobs())
            run_id = await trigger_client.trigger_enqueue("process-hearing", {"hearing_id": str(uuid4())})
            self.assertIsNone(run_id)
        ai_mode.clear_runtime_overrides()

    async def test_enqueue_mocked_when_cloud(self) -> None:
        from app.services import ai_mode, trigger_client

        ai_mode.clear_runtime_overrides()
        with patch.dict(
            "os.environ",
            {"HAKISCRIBE_AI_MODE": "cloud", "TRIGGER_SECRET_KEY": "secret"},
            clear=False,
        ):
            with patch("app.services.trigger_client.httpx.AsyncClient") as client_cls:
                client = MagicMock()
                client_cls.return_value.__aenter__.return_value = client
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.json.return_value = {"id": "run_abc"}

                async def _post(*_a, **_k):
                    return resp

                client.post = _post
                run_id = await trigger_client.trigger_enqueue("process-hearing", {"hearing_id": "x"})
                self.assertEqual(run_id, "run_abc")
        ai_mode.clear_runtime_overrides()


if __name__ == "__main__":
    unittest.main()
