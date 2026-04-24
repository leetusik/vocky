"""add action feedback fields

Revision ID: 20260424_1633
Revises: 20260423_2337
Create Date: 2026-04-24 16:33:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_1633"
down_revision: str | None = "20260423_2337"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit action feedback fields to feedback events."""

    op.add_column(
        "feedback_events",
        sa.Column("feedback_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("channel", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "feedback_events",
        sa.Column(
            "used_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index(
        "ix_feedback_events_feedback_value",
        "feedback_events",
        ["feedback_value"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_channel",
        "feedback_events",
        ["channel"],
        unique=False,
    )


def downgrade() -> None:
    """Remove explicit action feedback fields from feedback events."""

    op.drop_index("ix_feedback_events_channel", table_name="feedback_events")
    op.drop_index("ix_feedback_events_feedback_value", table_name="feedback_events")
    op.drop_column("feedback_events", "used_context")
    op.drop_column("feedback_events", "messages")
    op.drop_column("feedback_events", "channel")
    op.drop_column("feedback_events", "comment")
    op.drop_column("feedback_events", "feedback_value")
