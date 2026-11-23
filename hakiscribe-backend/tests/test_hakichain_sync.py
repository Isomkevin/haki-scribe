"""HakiChain inbound webhook sync (Phase 2)."""

from __future__ import annotations

import hashlib
import hmac
import os
import unittest
from unittest import mock
from uuid import uuid4

from app.models.schemas import HearingCreate, HearingSource, HearingStatus, Matter
from app.services import hakichain_sync, hearings, storage
from tests.stage_b_helpers import IsolatedStoreTestCase


class HakiChainSyncTests(IsolatedStoreTestCase):
    def test_verify_signature(self):
        secret = "test-secret"
        body = b'{"event":"matter.updated"}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        with mock.patch.dict(os.environ, {"HAKICHAIN_WEBHOOK_SECRET": secret}, clear=False):
            self.assertTrue(hakichain_sync.verify_signature(signature_header=f"sha256={digest}", body=body))
            self.assertFalse(hakichain_sync.verify_signature(signature_header="sha256=deadbeef", body=body))

    def test_hearing_filed_advances_local_status(self):
        matter = storage.create_matter(Matter(client_name="Acme", matter_name="Lease"))
        hearing = hearings.create_hearing(
            HearingCreate(source=HearingSource.manual_upload, title="Mention")
        )
        hearing.matter_id = matter.id
        hearing.status = HearingStatus.reviewed
        hearings._save()  # noqa: SLF001

        delivery = str(uuid4())
        result = hakichain_sync.apply_event(
            "hearing.filed",
            {
                "scribe_hearing_id": str(hearing.id),
                "hearing_id": "remote-1",
                "workspace_id": "ws-1",
                "status": "filed",
            },
            delivery_id=delivery,
        )
        self.assertTrue(result["ok"])
        updated = hearings.get_hearing(hearing.id)
        assert updated is not None
        self.assertEqual(updated.status, HearingStatus.filed)
        self.assertEqual(updated.platform_metadata["hakichain_sync"]["last_event"], "hearing.filed")

        # Idempotent on delivery id
        again = hakichain_sync.apply_event(
            "hearing.filed",
            {"scribe_hearing_id": str(hearing.id)},
            delivery_id=delivery,
        )
        self.assertTrue(again.get("reused"))

    def test_matter_updated_refreshes_fks(self):
        matter = storage.create_matter(Matter(client_name="Acme", matter_name="Lease"))
        storage.link_hakichain_matter(
            matter.id,
            hakichain_client_id="old",
            hakichain_workspace_id="11111111-1111-1111-1111-111111111111",
        )
        result = hakichain_sync.apply_event(
            "matter.updated",
            {
                "workspace_id": "11111111-1111-1111-1111-111111111111",
                "client_id": "ws-acme-new",
            },
            delivery_id=str(uuid4()),
        )
        self.assertTrue(result["ok"])
        refreshed = storage.get_matter(matter.id)
        assert refreshed is not None
        self.assertEqual(refreshed.hakichain_client_id, "ws-acme-new")


if __name__ == "__main__":
    unittest.main()
