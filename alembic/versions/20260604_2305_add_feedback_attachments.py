"""add feedback_attachments

Revision ID: 20260604_2305
Revises: 20260604_2116
Create Date: 2026-06-04 23:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260604_2305"
down_revision: str | None = "20260604_2116"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the feedback_attachments table and its indexes."""

    op.create_table(
        "feedback_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feedback_id", sa.UUID(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("claimed_user_id", sa.Text(), nullable=True),
        sa.Column("claimed_source_product", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback_attachments")),
        sa.ForeignKeyConstraint(
            ["feedback_id"],
            ["feedback_events.id"],
            name=op.f("fk_feedback_attachments_feedback_id_feedback_events"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_feedback_attachments_feedback_id",
        "feedback_attachments",
        ["feedback_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_attachments_feedback_id_created_at",
        "feedback_attachments",
        ["feedback_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_attachments_created_at",
        "feedback_attachments",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the feedback_attachments table and its indexes."""

    op.drop_index(
        "ix_feedback_attachments_created_at",
        table_name="feedback_attachments",
    )
    op.drop_index(
        "ix_feedback_attachments_feedback_id_created_at",
        table_name="feedback_attachments",
    )
    op.drop_index(
        "ix_feedback_attachments_feedback_id",
        table_name="feedback_attachments",
    )
    op.drop_table("feedback_attachments")
