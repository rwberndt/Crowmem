"""Initial schema: episodes, memories, beliefs, evidence, associations.

Revision ID: 0001
Revises:
Create Date: 2026-10-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384

MEMORY_TYPE = sa.Enum(
    "procedural", "failure", "constraint", "decision", "preference",
    "environment", "fact", "workflow", "warning", "pattern",
    name="memory_type",
)
BELIEF_STATUS = sa.Enum("active", "superseded", "disputed", "inactive", name="belief_status")
BELIEF_RELATION = sa.Enum("SUPPORTS", "SUPERSEDES", "CONTRADICTS", "REFINES", name="belief_relation")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "episodes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("salience_score", sa.Float(), nullable=True),
        sa.Column("encoded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("outcome_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_episodes_event_type", "episodes", ["event_type"])
    op.create_index("ix_episodes_project_id", "episodes", ["project_id"])

    op.create_table(
        "memories",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", MEMORY_TYPE, nullable=False),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_decayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("strength", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("utility_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("retrieval_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decay_rate", sa.Float(), nullable=False, server_default="0.02"),
        sa.Column("protected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    op.create_index("ix_memories_project_id", "memories", ["project_id"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])

    op.create_table(
        "beliefs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("predicate", sa.String(200), nullable=False),
        sa.Column("object", sa.String(500), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", BELIEF_STATUS, nullable=False, server_default="active"),
        sa.Column("superseded_by_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relation", BELIEF_RELATION, nullable=True),
    )
    op.create_foreign_key("fk_beliefs_superseded_by", "beliefs", "beliefs", ["superseded_by_id"], ["id"])
    op.create_index("ix_beliefs_subject", "beliefs", ["subject"])
    op.create_index("ix_beliefs_predicate", "beliefs", ["predicate"])
    op.create_index("ix_beliefs_subject_predicate_status", "beliefs", ["subject", "predicate", "status"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("memory_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=True),
        sa.Column("belief_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("beliefs.id"), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "associations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.create_index("ix_associations_memory_id", "associations", ["memory_id"])
    op.create_index("ix_associations_key", "associations", ["key"])
    op.create_index("ix_associations_value", "associations", ["value"])

    op.execute(
        "CREATE INDEX ix_episodes_embedding_hnsw ON episodes "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_memories_embedding_hnsw ON memories "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table("associations")
    op.drop_table("evidence")
    op.drop_table("beliefs")
    op.drop_table("memories")
    op.drop_table("episodes")
    BELIEF_RELATION.drop(op.get_bind(), checkfirst=True)
    BELIEF_STATUS.drop(op.get_bind(), checkfirst=True)
    MEMORY_TYPE.drop(op.get_bind(), checkfirst=True)
