"""Track answer streaks for the dynamic review schedule.

Revision ID: 20260727_10
Revises: 20260724_09
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_10"
down_revision: str | None = "20260724_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skill_mastery",
        sa.Column("consecutive_correct_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "skill_mastery",
        sa.Column("consecutive_incorrect_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("skill_mastery", "consecutive_correct_count", server_default=None)
    op.alter_column("skill_mastery", "consecutive_incorrect_count", server_default=None)


def downgrade() -> None:
    op.drop_column("skill_mastery", "consecutive_incorrect_count")
    op.drop_column("skill_mastery", "consecutive_correct_count")
