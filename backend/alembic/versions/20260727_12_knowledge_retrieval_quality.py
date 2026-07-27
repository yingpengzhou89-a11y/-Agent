"""Persist knowledge retrieval events and citation feedback.

Revision ID: 20260727_12
Revises: 20260727_11
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_12"
down_revision: str | None = "20260727_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_search_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("result_chunk_ids_json", sa.JSON(), nullable=False),
        sa.Column("retrieval_config_json", sa.JSON(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_search_events_user_id", "knowledge_search_events", ["user_id"])
    op.create_table(
        "knowledge_search_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("search_event_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("relevance", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_event_id"], ["knowledge_search_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_event_id", "chunk_id", name="uq_search_feedback_event_chunk"),
    )
    op.create_index("ix_knowledge_search_feedback_user_id", "knowledge_search_feedback", ["user_id"])
    op.create_index("ix_knowledge_search_feedback_search_event_id", "knowledge_search_feedback", ["search_event_id"])
    op.create_index("ix_knowledge_search_feedback_chunk_id", "knowledge_search_feedback", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_search_feedback_chunk_id", table_name="knowledge_search_feedback")
    op.drop_index("ix_knowledge_search_feedback_search_event_id", table_name="knowledge_search_feedback")
    op.drop_index("ix_knowledge_search_feedback_user_id", table_name="knowledge_search_feedback")
    op.drop_table("knowledge_search_feedback")
    op.drop_index("ix_knowledge_search_events_user_id", table_name="knowledge_search_events")
    op.drop_table("knowledge_search_events")
