"""add user password hash

Revision ID: 0013_add_user_password_hash
Revises: YOUR_CURRENT_ALEMBIC_HEAD
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_add_user_password_hash"
down_revision: str | None = "20260727_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")