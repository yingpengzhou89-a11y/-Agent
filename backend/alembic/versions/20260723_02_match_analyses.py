"""Create persisted match analysis reports.

Revision ID: 20260723_02
Revises: 20260723_01
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_02"
down_revision: str | None = "20260723_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_analyses_user_id", "match_analyses", ["user_id"])
    op.create_index("ix_match_analyses_resume_id", "match_analyses", ["resume_id"])
    op.create_index("ix_match_analyses_job_id", "match_analyses", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_match_analyses_job_id", table_name="match_analyses")
    op.drop_index("ix_match_analyses_resume_id", table_name="match_analyses")
    op.drop_index("ix_match_analyses_user_id", table_name="match_analyses")
    op.drop_table("match_analyses")
