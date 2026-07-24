"""Persist reproducible evaluation metadata and deterministic checks.

Revision ID: 20260724_09
Revises: 20260724_08
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260724_09"
down_revision: str | None = "20260724_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("answer_evaluations", sa.Column("rubric_json", sa.JSON(), nullable=True))
    op.add_column("answer_evaluations", sa.Column("generation_config_json", sa.JSON(), nullable=True))
    op.add_column("answer_evaluations", sa.Column("deterministic_checks_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("answer_evaluations", "deterministic_checks_json")
    op.drop_column("answer_evaluations", "generation_config_json")
    op.drop_column("answer_evaluations", "rubric_json")
