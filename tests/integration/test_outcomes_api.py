from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor

CANDIDATE = MemoryCandidate(
    content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
    memory_type="warning", risk_score=0.95, confidence=0.9,
    associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
)


def _seed_and_recall(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)
    client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error", "project_id": "peach",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )
    recall_resp = client.post(
        "/recall",
        json={"query": "Deploy the API", "goal_state": {"project": "peach", "environment": "production", "task": "database_migration"}},
    )
    body = recall_resp.json()
    memory_id = body["working_memory"][0]["id"]
    return body["retrieval_id"], memory_id


def test_successful_outcome_raises_utility_not_confidence(client, monkeypatch):
    retrieval_id, memory_id = _seed_and_recall(client, monkeypatch)
    before = client.get(f"/memories/{memory_id}").json()

    resp = client.post("/outcomes", json={"retrieval_id": retrieval_id, "outcome": "success", "used_memory_ids": [memory_id], "reward": 1.0})
    assert resp.status_code == 200

    after = client.get(f"/memories/{memory_id}").json()
    assert after["utility_score"] > before["utility_score"]
    assert after["successful_use_count"] == before["successful_use_count"] + 1
    assert after["confidence"] == before["confidence"]  # invariants 2/3


def test_confirm_raises_confidence_not_utility(client, monkeypatch):
    _, memory_id = _seed_and_recall(client, monkeypatch)
    before = client.get(f"/memories/{memory_id}").json()

    resp = client.patch(f"/memories/{memory_id}/confirm", json={})
    assert resp.status_code == 200
    after = resp.json()

    assert after["confidence"] > before["confidence"]
    assert after["utility_score"] == before["utility_score"]
    assert after["strength"] == before["strength"]


def test_correct_lowers_confidence_not_utility(client, monkeypatch):
    _, memory_id = _seed_and_recall(client, monkeypatch)
    before = client.get(f"/memories/{memory_id}").json()

    resp = client.patch(f"/memories/{memory_id}/correct", json={})
    after = resp.json()

    assert after["confidence"] < before["confidence"]
    assert after["utility_score"] == before["utility_score"]


def test_unknown_retrieval_id_returns_404(client):
    import uuid

    resp = client.post("/outcomes", json={"retrieval_id": str(uuid.uuid4()), "outcome": "success", "used_memory_ids": []})
    assert resp.status_code == 404
