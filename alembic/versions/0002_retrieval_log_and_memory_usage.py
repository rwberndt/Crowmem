"""retrieval_log and memory_usage tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USAGE_OUTCOME = sa.Enum("success", "failure", "neutral", "unknown", name="usage_outcome")


def upgrade() -> None:
    op.create_table(
        "retrieval_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("goal_state", sa.dialects.postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("returned_memory_ids", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scores_and_reasons", sa.dialects.postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "memory_usage",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column(
            "retrieval_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("retrieval_log.id"), nullable=False
        ),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("outcome", USAGE_OUTCOME, nullable=True),
        sa.Column("reward", sa.Float(), nullable=True),
    )
    op.create_index("ix_memory_usage_memory_id", "memory_usage", ["memory_id"])
    op.create_index("ix_memory_usage_retrieval_id", "memory_usage", ["retrieval_id"])


def downgrade() -> None:
    op.drop_table("memory_usage")
    op.drop_table("retrieval_log")
    USAGE_OUTCOME.drop(op.get_bind(), checkfirst=True)
