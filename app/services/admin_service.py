from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.pricing_config import PricingConfig
from app.models.belief import Belief
from app.models.episode import Episode
from app.models.memory import Memory
from app.models.retrieval_log import RetrievalLog
from app.models.usage_log import UsageLog
from app.repositories.usage_log_repository import UsageLogRepository

# Deleting these four project-scoped parent tables is sufficient: evidence,
# associations, and memory_usage all cascade (ON DELETE CASCADE, migration
# 0003) from episodes/memories/beliefs/retrieval_log. usage_log has no FK
# to cascade from, so it's wiped explicitly.
_PROJECT_SCOPED_MODELS = (Episode, Memory, Belief, RetrievalLog, UsageLog)


def wipe_project(db: Session, project_id: str) -> dict[str, int]:
    """Used by the Mem Off adapter's wipe.sh (guide: 'wipe_check.sh exits
    non-zero when the store is not empty; the runner calls it after
    wipe.sh'). A single project_id delete per table; cascades handle the
    rest within the same transaction.
    """
    counts: dict[str, int] = {}
    for model in _PROJECT_SCOPED_MODELS:
        result = db.execute(delete(model).where(model.project_id == project_id))
        counts[model.__tablename__] = result.rowcount
    db.commit()
    return counts


def count_project_rows(db: Session, project_id: str) -> dict[str, int]:
    """Used by wipe_check.sh to verify a wipe actually emptied the store."""
    counts: dict[str, int] = {}
    for model in _PROJECT_SCOPED_MODELS:
        stmt = select(func.count()).select_from(model).where(model.project_id == project_id)
        counts[model.__tablename__] = db.execute(stmt).scalar_one()
    return counts


def summarize_usage(
    db: Session, project_id: str, since: datetime | None, pricing: PricingConfig
) -> list[dict]:
    """Used by usage.sh (CONTRACT.md: '[{"id", "source": "server",
    "tokens_in", "tokens_out", "cost_usd", "token_basis", "cost_basis"}]').
    One row per call_type/model pair so a model swap mid-run is still
    itemized rather than averaged away.
    """
    rows = UsageLogRepository(db).list_since(project_id, since)
    totals: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (row.call_type, row.model)
        bucket = totals.setdefault(key, {"tokens_in": 0, "tokens_out": 0})
        bucket["tokens_in"] += row.input_tokens
        bucket["tokens_out"] += row.output_tokens

    records = []
    for (call_type, model), bucket in totals.items():
        cost = pricing.cost_usd(model, bucket["tokens_in"], bucket["tokens_out"])
        records.append(
            {
                "id": call_type,
                "source": "server",
                "tokens_in": bucket["tokens_in"],
                "tokens_out": bucket["tokens_out"],
                "cost_usd": cost,
                "token_basis": model,
                "cost_basis": "config/llm_pricing.yaml" if cost is not None else "unknown_model_pricing",
            }
        )
    return records
