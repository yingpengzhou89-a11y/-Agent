"""Add native PostgreSQL full-text index for knowledge chunks.

Revision ID: 20260727_11
Revises: 20260727_10
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260727_11"
down_revision: str | None = "20260727_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_document_chunks_content_fts "
        "ON document_chunks USING gin (to_tsvector('simple', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_document_chunks_content_fts")
