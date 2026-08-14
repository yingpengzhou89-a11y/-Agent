"""create audit logs

Revision ID: 0014_create_audit_logs
Revises: 0013_add_user_password_hash
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_create_audit_logs"
down_revision: str | None = "0013_add_user_password_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "resource_type",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "resource_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "status_code",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "request_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_audit_logs_created_at",
        "audit_logs",
        ["created_at"],
    )

    op.create_index(
        "ix_audit_logs_actor_user_id",
        "audit_logs",
        ["actor_user_id"],
    )

    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
    )

    op.create_index(
        "ix_audit_logs_request_id",
        "audit_logs",
        ["request_id"],
    )

    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_logs_resource",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_request_id",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_action",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_actor_user_id",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_created_at",
        table_name="audit_logs",
    )

    op.drop_table("audit_logs")
