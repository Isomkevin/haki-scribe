"""Hearing pack filing into external HakiChain WorkSpace."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.models.schemas import (
    HearingConfirmRequest,
    HearingCreate,
    HearingSource,
    HearingStatus,
    Matter,
    Session,
    SessionSource,
    TranscriptSegment,
)
from app.services import hearing_filing, hearings, storage
from tests.stage_b_helpers import IsolatedStoreTestCase


def _run(coro):
    return asyncio.run(coro)


class HearingFilingTests(IsolatedStoreTestCase):
    def _reviewed_hearing(self):
        matter = storage.create_matter(
            Matter(client_name="Acme Holdings", matter_name="HCCC E123 of 2024 lease")
        )
        hearing = hearings.create_hearing(
            HearingCreate(
                source=HearingSource.manual_upload,
                title="Acme Holdings HCCC No. E123 of 2024 mention",
                case_reference="E123/2024",
            )
        )
        hearings.propose_matches(hearing.id)
        hearings.confirm_match(
            hearing.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id)
        )
        session = storage.create_session(Session(title=hearing.title, source=SessionSource.mic))
        hearing = hearings.get_hearing(hearing.id)
        assert hearing is not None
        hearing.session_id = session.id
        hearing.status = HearingStatus.transcribed
        hearing.platform_metadata = {
            "proceedings": {
                "rules": [
                    {
                        "kind": "next_date",
                        "method": "rules",
                        "text": "Mention on 15 January 2025",
                        "date": "2025-01-15T09:00:00",
                        "quote": "Matter stood over to 15th January 2025",
                        "purpose": "Mention",
                    }
                ],
                "llm": {"items": [], "ungrounded": []},
            }
        }
        hearings._save()  # noqa: SLF001
        hearings.mark_reviewed(hearing.id)
        storage.replace_transcript(
            session.id,
            [
                TranscriptSegment(
                    session_id=session.id,
                    speaker="Court",
                    text="Matter stood over to 15th January 2025 for mention.",
                    start_ms=1000,
                    end_ms=4000,
                )
            ],
        )
        return hearings.get_hearing(hearing.id), matter

    def test_requires_reviewed_status(self):
        matter = storage.create_matter(Matter(client_name="A", matter_name="B"))
        hearing = hearings.create_hearing(
            HearingCreate(source=HearingSource.manual_upload, title="Early hearing")
        )
        hearings.propose_matches(hearing.id)
        hearings.confirm_match(
            hearing.id, HearingConfirmRequest(decision="confirm", matter_id=matter.id)
        )
        with self.assertRaises(hearing_filing.FilingError) as ctx:
            _run(hearing_filing.file_hearing_pack(hearing.id))
        self.assertIn("reviewed", str(ctx.exception).lower())

    def test_requires_hakichain_connection(self):
        hearing, _ = self._reviewed_hearing()
        with patch("app.integrations.hakichain_client.configured", return_value=False):
            with self.assertRaises(hearing_filing.FilingError) as ctx:
                _run(hearing_filing.file_hearing_pack(hearing.id))
        self.assertIn("not connected", str(ctx.exception).lower())

    def test_files_pack_and_marks_filed(self):
        hearing, matter = self._reviewed_hearing()
        assert hearing is not None

        async def fake_matter(**kwargs):
            self.assertEqual(kwargs["scribe_matter_id"], str(matter.id))
            return {
                "ok": True,
                "client_id": f"hs-{matter.id}",
                "workspace_url": f"https://hakichain.com/workspace?ws=hs-{matter.id}",
            }

        async def fake_document(**kwargs):
            self.assertIn("Hearing", kwargs["title"])
            self.assertTrue(kwargs["document_text"])
            return {
                "ok": True,
                "client_id": kwargs.get("client_id"),
                "workspace_url": f"https://hakichain.com/workspace?ws={kwargs.get('client_id')}",
            }

        async def fake_reminder(**kwargs):
            self.assertEqual(kwargs["start"], "2025-01-15T09:00:00")
            return {
                "ok": True,
                "client_id": kwargs.get("client_id"),
                "workspace_url": f"https://hakichain.com/workspace?ws={kwargs.get('client_id')}",
            }

        with patch("app.integrations.hakichain_client.configured", return_value=True), patch(
            "app.integrations.hakichain_client.file_matter", new=AsyncMock(side_effect=fake_matter)
        ) as file_matter, patch(
            "app.integrations.hakichain_client.file_document", new=AsyncMock(side_effect=fake_document)
        ) as file_document, patch(
            "app.integrations.hakichain_client.file_reminder", new=AsyncMock(side_effect=fake_reminder)
        ) as file_reminder:
            result = _run(hearing_filing.file_hearing_pack(hearing.id))

        self.assertTrue(result["ok"])
        self.assertEqual(file_matter.await_count, 1)
        self.assertEqual(file_document.await_count, 2)
        self.assertEqual(file_reminder.await_count, 1)
        self.assertTrue(result["steps"]["transcript"]["ok"])
        self.assertTrue(result["steps"]["proceedings"]["ok"])
        self.assertTrue(result["steps"]["reminders"][0]["ok"])
        filed = hearings.get_hearing(hearing.id)
        assert filed is not None
        self.assertEqual(filed.status, HearingStatus.filed)
        self.assertIn("hakichain_filing", filed.platform_metadata or {})
        self.assertIn("workspace?ws=", result["workspace_url"] or "")

    def test_partial_document_failure_raises(self):
        hearing, _ = self._reviewed_hearing()

        with patch("app.integrations.hakichain_client.configured", return_value=True), patch(
            "app.integrations.hakichain_client.file_matter",
            new=AsyncMock(return_value={"ok": True, "client_id": "hs-x"}),
        ), patch(
            "app.integrations.hakichain_client.file_document", new=AsyncMock(return_value=None)
        ), patch(
            "app.integrations.hakichain_client.file_reminder", new=AsyncMock(return_value=None)
        ), patch(
            "app.integrations.hakichain_client.last_error", return_value="ingress 503"
        ):
            with self.assertRaises(hearing_filing.FilingError) as ctx:
                _run(hearing_filing.file_hearing_pack(hearing.id))
        self.assertIn("failed", str(ctx.exception).lower())
        still = hearings.get_hearing(hearing.id)
        assert still is not None
        self.assertEqual(still.status, HearingStatus.reviewed)

    def test_proceedings_pack_marks_ai_disclaimer(self):
        hearing = hearings.create_hearing(
            HearingCreate(source=HearingSource.manual_upload, title="Demo hearing")
        )
        hearing.platform_metadata = {
            "proceedings": {
                "rules": [],
                "llm": {
                    "items": [
                        {
                            "kind": "order",
                            "method": "llm",
                            "text": "Costs in the cause",
                            "quote": "costs in the cause",
                        }
                    ],
                    "ungrounded": [{"kind": "direction", "text": "File submissions", "reason": "no quote"}],
                },
            }
        }
        text = hearing_filing._format_proceedings(hearing)  # noqa: SLF001
        self.assertIn("NOT authenticated court orders", text)
        self.assertIn("Costs in the cause", text)
        self.assertIn("Ungrounded", text)


if __name__ == "__main__":
    import unittest

    unittest.main()
