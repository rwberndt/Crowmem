from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor

CANDIDATE = MemoryCandidate(
    content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
    memory_type="warning",
    risk_score=0.95,
    confidence=0.9,
    associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
)


def _seed_memory(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)
    client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error",
            "project_id": "peach",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )


def test_memory_activates_via_goal_context_despite_unrelated_query_text(client, monkeypatch):
    """The guide's core corvid-inspired claim (section 26): a production
    migration warning activates for a goal matching its associations even
    though the query never says 'migrate dev'."""
    _seed_memory(client, monkeypatch)

    resp = client.post(
        "/recall",
        json={
            "query": "Deploy the API",
            "goal_state": {
                "project": "peach", "task": "database_migration", "environment": "production",
                "active_tools": ["prisma"], "active_files": ["prisma/schema.prisma"],
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["working_memory"]) == 1
    item = body["working_memory"][0]
    assert "environment_match" in item["reason"]
    assert "task_match" in item["reason"]


def test_recall_requires_project_in_goal_state(client):
    resp = client.post("/recall", json={"query": "anything", "goal_state": {}})
    assert resp.status_code == 400


def test_recall_respects_max_memories_bound(client, monkeypatch):
    _seed_memory(client, monkeypatch)
    resp = client.post(
        "/recall",
        json={"query": "x", "goal_state": {"project": "peach", "environment": "production"}, "max_memories": 1},
    )
    assert len(resp.json()["working_memory"]) <= 1


def test_recall_persists_retrieval_log_and_memory_usage(client, monkeypatch, db_session):
    _seed_memory(client, monkeypatch)
    resp = client.post(
        "/recall",
        json={"query": "Deploy the API", "goal_state": {"project": "peach", "environment": "production", "task": "database_migration"}},
    )
    retrieval_id = resp.json()["retrieval_id"]

    from app.repositories.retrieval_repository import RetrievalRepository

    repo = RetrievalRepository(db_session)
    log = repo.get_log(retrieval_id)
    assert log is not None
    usage_rows = repo.list_usage_for_retrieval(retrieval_id)
    assert len(usage_rows) == len(resp.json()["working_memory"])
    assert all(row.used is False for row in usage_rows)  # not yet reported via /outcomes
