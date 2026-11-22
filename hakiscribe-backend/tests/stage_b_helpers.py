"""Shared isolation for Stage B hearing tests.

storage.py snapshots to data/store.json (the developer's demo library), so
tests swap every in-memory dict, disable persistence, and point recordings at
a temp dir. Nothing a test does reaches the real store or recordings volume.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from unittest import mock

import httpx

from app.services import ai_mode, ai_runs, hearings, storage
from app.services.court_adapters import base as adapter_base

_STORE_DICTS = (
    "_sessions",
    "_transcripts",
    "_actions",
    "_flags",
    "_matters",
    "_contacts",
    "_results",
    "_session_matter_ids",
    "_session_contact_ids",
    "_chats",
)


class IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._patches = [mock.patch.object(storage, "_persist", lambda: None)]
        for name in _STORE_DICTS:
            self._patches.append(mock.patch.dict(getattr(storage, name), clear=True))
        self._tmp = tempfile.mkdtemp(prefix="hakiscribe-test-")
        self._patches.append(mock.patch.dict(os.environ, {"HAKISCRIBE_RECORDINGS_DIR": self._tmp}))
        for p in self._patches:
            p.start()
        hearings.reset()
        ai_mode.clear_runtime_overrides()
        ai_runs.clear()

    def tearDown(self) -> None:
        for p in reversed(self._patches):
            p.stop()
        hearings.reset()
        ai_mode.clear_runtime_overrides()
        adapter_base._transport = None
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def mock_http(self, handler) -> None:
        """Route court-adapter HTTP through `handler(request) -> httpx.Response`."""
        adapter_base._transport = httpx.MockTransport(handler)
