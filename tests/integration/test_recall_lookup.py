import uuid


def test_get_retrieval_by_id_returns_404_when_missing(client):
    resp = client.get(f"/recall/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_retrieval_by_id_returns_reasons(client):
    recall_resp = client.post("/recall", json={"query": "x", "goal_state": {"project": "peach"}})
    retrieval_id = recall_resp.json()["retrieval_id"]

    resp = client.get(f"/recall/{retrieval_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["retrieval_id"] == retrieval_id
    assert body["project_id"] == "peach"
    assert "scores_and_reasons" in body


def test_list_recent_retrievals_for_project(client):
    client.post("/recall", json={"query": "a", "goal_state": {"project": "peach-recent"}})
    client.post("/recall", json={"query": "b", "goal_state": {"project": "peach-recent"}})

    resp = client.get("/recall", params={"project_id": "peach-recent", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(r["project_id"] == "peach-recent" for r in body)
