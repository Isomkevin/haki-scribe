import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.schemas import ActionType, DetectedAction
from app.services.demo_library import generate


class TriggerResultNormalisationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_accepts_mapping_and_json_string_items(self):
        session_id = uuid.uuid4()
        actions = [
            DetectedAction(
                session_id=session_id,
                type=ActionType.private_note,
                title="Note",
                preview="Record the instruction",
                confidence=1,
            ),
            DetectedAction(
                session_id=session_id,
                type=ActionType.time_entry,
                title="Time",
                preview="Record time",
                confidence=1,
            ),
        ]
        raw = {
            "json": [
                {
                    "action_id": str(actions[0].id),
                    "type": "private_note",
                    "status": "success",
                    "result": {"note_text": "Follow up Friday"},
                },
                json.dumps(
                    {
                        "action_id": str(actions[1].id),
                        "type": "time_entry",
                        "status": "success",
                        "result": {"duration_hours": 0.5},
                    }
                ),
            ]
        }

        with patch(
            "app.services.demo_library.trigger_client.trigger_and_wait",
            new=AsyncMock(return_value=raw),
        ):
            results = await generate(SimpleNamespace(transcript=[]), actions)

        self.assertEqual([result.status for result in results], ["success", "success"])
        self.assertEqual(results[1].result["duration_hours"], 0.5)


if __name__ == "__main__":
    unittest.main()
