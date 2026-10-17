from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, empty_memory_result


def test_high_salience_event_is_encoded(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", empty_memory_result)
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    resp = client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error",
            "project_id": "peach",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["encoded"] is True
    assert body["salience_score"] >= 0.25


def test_low_salience_event_is_not_encoded(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", empty_memory_result)
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    resp = client.post(
        "/events",
        json={"content": "Opened README.md to check project description.", "event_type": "file_read", "project_id": "peach"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["encoded"] is False
    assert body["salience_score"] < 0.25


def test_episode_has_no_update_route(client):
    resp = client.post(
        "/events", json={"content": "x", "event_type": "observation", "project_id": "peach"}
    )
    episode_id = resp.json()["id"]
    # Guide invariant 1: episodes are immutable -- no PATCH/PUT route exists.
    put_resp = client.put(f"/episodes/{episode_id}", json={"content": "y"})
    assert put_resp.status_code in (404, 405)
