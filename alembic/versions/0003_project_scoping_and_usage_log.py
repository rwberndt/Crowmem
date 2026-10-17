"""Project-scope beliefs/retrieval_log, cascading deletes, usage_log table.

Driven by the Mem Off adapter work: a project wipe must be verified empty
and must not leak across stores, which needs every table reachable by
project_id and FK cleanup cascading from the four project-scoped parents
(episodes, memories, beliefs, retrieval_log).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- beliefs.project_id ---
    op.add_column("beliefs", sa.Column("project_id", sa.String(100), nullable=True))
    op.execute("UPDATE beliefs SET project_id = 'unknown' WHERE project_id IS NULL")
    op.alter_column("beliefs", "project_id", nullable=False)
    op.create_index("ix_beliefs_project_id", "beliefs", ["project_id"])

    # --- retrieval_log.project_id (backfilled from the goal_state JSONB) ---
    op.add_column("retrieval_log", sa.Column("project_id", sa.String(100), nullable=True))
    op.execute("UPDATE retrieval_log SET project_id = COALESCE(goal_state->>'project', 'unknown')")
    op.alter_column("retrieval_log", "project_id", nullable=False)
    op.create_index("ix_retrieval_log_project_id", "retrieval_log", ["project_id"])

    # --- cascading deletes, so wiping a project is a plain parent-row delete ---
    op.drop_constraint("evidence_episode_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_episode_id_fkey", "evidence", "episodes", ["episode_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("evidence_memory_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_memory_id_fkey", "evidence", "memories", ["memory_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("evidence_belief_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_belief_id_fkey", "evidence", "beliefs", ["belief_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("associations_memory_id_fkey", "associations", type_="foreignkey")
    op.create_foreign_key("associations_memory_id_fkey", "associations", "memories", ["memory_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("memory_usage_memory_id_fkey", "memory_usage", type_="foreignkey")
    op.create_foreign_key("memory_usage_memory_id_fkey", "memory_usage", "memories", ["memory_id"], ["id"], ondelete="CASCADE")

    op.drop_constraint("memory_usage_retrieval_id_fkey", "memory_usage", type_="foreignkey")
    op.create_foreign_key(
        "memory_usage_retrieval_id_fkey", "memory_usage", "retrieval_log", ["retrieval_id"], ["id"], ondelete="CASCADE"
    )

    # Self-referential: SET NULL, not CASCADE -- deleting the newer belief in
    # a wipe shouldn't try to cascade-delete the older one it superseded.
    op.drop_constraint("fk_beliefs_superseded_by", "beliefs", type_="foreignkey")
    op.create_foreign_key(
        "fk_beliefs_superseded_by", "beliefs", "beliefs", ["superseded_by_id"], ["id"], ondelete="SET NULL"
    )

    # --- usage_log ---
    op.create_table(
        "usage_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("call_type", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_usage_log_project_id", "usage_log", ["project_id"])
    op.create_index("ix_usage_log_created_at", "usage_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("usage_log")

    op.drop_constraint("fk_beliefs_superseded_by", "beliefs", type_="foreignkey")
    op.create_foreign_key("fk_beliefs_superseded_by", "beliefs", "beliefs", ["superseded_by_id"], ["id"])

    op.drop_constraint("memory_usage_retrieval_id_fkey", "memory_usage", type_="foreignkey")
    op.create_foreign_key("memory_usage_retrieval_id_fkey", "memory_usage", "retrieval_log", ["retrieval_id"], ["id"])

    op.drop_constraint("memory_usage_memory_id_fkey", "memory_usage", type_="foreignkey")
    op.create_foreign_key("memory_usage_memory_id_fkey", "memory_usage", "memories", ["memory_id"], ["id"])

    op.drop_constraint("associations_memory_id_fkey", "associations", type_="foreignkey")
    op.create_foreign_key("associations_memory_id_fkey", "associations", "memories", ["memory_id"], ["id"])

    op.drop_constraint("evidence_belief_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_belief_id_fkey", "evidence", "beliefs", ["belief_id"], ["id"])

    op.drop_constraint("evidence_memory_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_memory_id_fkey", "evidence", "memories", ["memory_id"], ["id"])

    op.drop_constraint("evidence_episode_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key("evidence_episode_id_fkey", "evidence", "episodes", ["episode_id"], ["id"])

    op.drop_index("ix_retrieval_log_project_id", "retrieval_log")
    op.drop_column("retrieval_log", "project_id")

    op.drop_index("ix_beliefs_project_id", "beliefs")
    op.drop_column("beliefs", "project_id")
