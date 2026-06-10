"""add feedback_comments

Revision ID: 20260604_2116
Revises: 20260429_1620
Create Date: 2026-06-04 21:16:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260604_2116"
down_revision: str | None = "20260429_1620"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the feedback_comments table and its indexes."""

    op.create_table(
        "feedback_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("feedback_id", sa.UUID(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback_comments")),
        sa.ForeignKeyConstraint(
            ["feedback_id"],
            ["feedback_events.id"],
            name=op.f("fk_feedback_comments_feedback_id_feedback_events"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_feedback_comments_feedback_id",
        "feedback_comments",
        ["feedback_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_comments_feedback_id_created_at",
        "feedback_comments",
        ["feedback_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the feedback_comments table and its indexes."""

    op.drop_index(
        "ix_feedback_comments_feedback_id_created_at",
        table_name="feedback_comments",
    )
    op.drop_index(
        "ix_feedback_comments_feedback_id",
        table_name="feedback_comments",
    )
    op.drop_table("feedback_comments")
