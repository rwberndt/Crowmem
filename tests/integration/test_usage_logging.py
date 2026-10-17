from app.repositories.usage_log_repository import UsageLogRepository
from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import FAKE_USAGE, empty_belief_result, make_memory_extractor

CANDIDATE = MemoryCandidate(
    content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
    memory_type="warning", risk_score=0.95, confidence=0.9,
    associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
)


def test_usage_is_logged_for_every_llm_call_even_with_no_candidates(client, monkeypatch, db_session):
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

    usage_repo = UsageLogRepository(db_session)
    rows = usage_repo.list_since("peach", None)
    call_types = {row.call_type for row in rows}

    # Both calls happen for every encoded episode, regardless of whether
    # either produced candidates -- tokens are spent on the call, not the result.
    assert call_types == {"extract_memories", "extract_belief_candidates"}
    assert all(row.input_tokens == FAKE_USAGE.input_tokens for row in rows)
    assert all(row.output_tokens == FAKE_USAGE.output_tokens for row in rows)
