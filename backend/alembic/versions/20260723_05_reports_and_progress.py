"""Create interview report and skill mastery tables.

Revision ID: 20260723_05
Revises: 20260723_04
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_05"
down_revision: str | None = "20260723_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("weak_topics_json", sa.JSON(), nullable=False),
        sa.Column("recommended_actions_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_interview_reports_session_id", "interview_reports", ["session_id"])
    op.create_table(
        "skill_mastery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_score", sa.Float(), nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_name", name="uq_skill_mastery_user_skill"),
    )
    op.create_index("ix_skill_mastery_user_id", "skill_mastery", ["user_id"])
    op.create_index("ix_skill_mastery_next_review_at", "skill_mastery", ["next_review_at"])


def downgrade() -> None:
    op.drop_index("ix_skill_mastery_next_review_at", table_name="skill_mastery")
    op.drop_index("ix_skill_mastery_user_id", table_name="skill_mastery")
    op.drop_table("skill_mastery")
    op.drop_index("ix_interview_reports_session_id", table_name="interview_reports")
    op.drop_table("interview_reports")
