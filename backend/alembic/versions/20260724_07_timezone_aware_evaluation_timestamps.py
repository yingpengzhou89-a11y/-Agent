"""Use timezone-aware timestamps for evaluation and progress records.

Revision ID: 20260724_07
Revises: 20260724_06
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260724_07"
down_revision: str | None = "20260724_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table, column in (
        ("answer_evaluations", "created_at"),
        ("interview_reports", "created_at"),
        ("skill_mastery", "updated_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=False),
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in (
        ("skill_mastery", "updated_at"),
        ("interview_reports", "created_at"),
        ("answer_evaluations", "created_at"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
