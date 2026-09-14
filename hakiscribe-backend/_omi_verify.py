"""One-shot verification for Omi Miniapp paths. Delete after use."""
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Session, SessionSource, SessionStatus
from app.services import omi_pairing, storage

client = TestClient(app)

omi_pairing.unlink()

r = client.get("/integrations/omi/auth?uid=test-uid")
assert r.status_code == 200 and "linked" in r.text.lower(), r.text[:200]
r = client.get("/integrations/omi/setup-completed?uid=test-uid")
assert r.json() == {"is_setup_completed": True}, r.json()
r = client.get("/integrations/omi/status")
assert r.json()["linked"] is True and r.json()["uid"] == "test-uid", r.json()
health = client.get("/health").json()
assert health["integrations"]["omi"] is True
assert health["omi_miniapp"]["linked"] is True

r = client.post(
    "/webhooks/omi?uid=test-uid&session_id=omi-conv-1",
    json=[{"text": "Hello from Omi", "speaker": "Speaker 1", "start": 0, "end": 1.5}],
)
assert r.status_code == 200, r.text
body = r.json()
assert body["received"] == 1 and body["uid"] == "test-uid"
sid1 = body["session_id"]
detail = client.get(f"/sessions/{sid1}").json()
assert detail["source"] == "omi"
assert any("Hello from Omi" in s["text"] for s in detail["transcript"])

r = client.post(
    "/webhooks/omi?uid=test-uid&session_id=omi-conv-1",
    json=[{"text": "Second chunk", "speaker": "Speaker 1", "start": 2, "end": 3}],
)
assert r.status_code == 200 and r.json()["session_id"] == sid1, r.json()

r = client.post(
    "/webhooks/omi?uid=test-uid&session_id=omi-mem-9",
    json={
        "id": "omi-mem-9",
        "structured": {"title": "Client intake memory"},
        "transcript_segments": [
            {"text": "We agreed on Friday", "speaker": "SPEAKER_0", "start": 0, "end": 2}
        ],
    },
)
assert r.status_code == 200, r.text
mem_id = r.json()["session_id"]
assert mem_id != sid1
mem = client.get(f"/sessions/{mem_id}").json()
assert mem["title"] == "Client intake memory"
assert mem["status"] == "ready"

legacy = storage.create_session(
    Session(title="Legacy pair", source=SessionSource.omi, status=SessionStatus.recording)
)
r = client.post(
    f"/webhooks/omi?session_id={legacy.id}",
    json={
        "session_external_id": str(legacy.id),
        "segments": [{"text": "Legacy seg", "speaker": "A", "start_ms": 0, "end_ms": 1000}],
    },
)
assert r.status_code == 200 and r.json()["session_id"] == str(legacy.id), r.json()

omi_pairing.unlink()
r = client.post(
    "/webhooks/omi?uid=test-uid",
    json=[{"text": "Nope", "start": 0, "end": 1}],
)
assert r.status_code == 403, r.text
r = client.get("/integrations/omi/setup-completed?uid=test-uid")
assert r.json() == {"is_setup_completed": False}
print("ALL OMI CHECKS PASSED")
