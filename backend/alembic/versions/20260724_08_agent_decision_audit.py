"""Persist Agent decision audit records.

Revision ID: 20260724_08
Revises: 20260724_07
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260724_08"
down_revision: str | None = "20260724_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_decision_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("input_summary_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_decision_logs_user_id", "agent_decision_logs", ["user_id"])
    op.create_index("ix_agent_decision_logs_session_id", "agent_decision_logs", ["session_id"])
    op.create_index("ix_agent_decision_logs_agent_name", "agent_decision_logs", ["agent_name"])


def downgrade() -> None:
    op.drop_index("ix_agent_decision_logs_agent_name", table_name="agent_decision_logs")
    op.drop_index("ix_agent_decision_logs_session_id", table_name="agent_decision_logs")
    op.drop_index("ix_agent_decision_logs_user_id", table_name="agent_decision_logs")
    op.drop_table("agent_decision_logs")
