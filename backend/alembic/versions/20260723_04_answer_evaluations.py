"""Create persisted answer evaluations.

Revision ID: 20260723_04
Revises: 20260723_03
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_04"
down_revision: str | None = "20260723_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("answer_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("dimension_scores_json", sa.JSON(), nullable=False),
        sa.Column("strengths_json", sa.JSON(), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.Column("missing_points_json", sa.JSON(), nullable=False),
        sa.Column("advice_json", sa.JSON(), nullable=False),
        sa.Column("answer_framework_json", sa.JSON(), nullable=False),
        sa.Column("improved_answer", sa.Text(), nullable=False),
        sa.Column("practice_questions_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["interview_answers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("answer_id"),
    )
    op.create_index("ix_answer_evaluations_answer_id", "answer_evaluations", ["answer_id"])


def downgrade() -> None:
    op.drop_index("ix_answer_evaluations_answer_id", table_name="answer_evaluations")
    op.drop_table("answer_evaluations")
