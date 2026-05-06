"""add identity and trigger fields

Revision ID: 20260429_1620
Revises: 20260429_1103
Create Date: 2026-04-29 16:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260429_1620"
down_revision: str | None = "20260429_1103"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add optional identity and trigger capture fields."""

    op.add_column(
        "feedback_events",
        sa.Column("user_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("trigger_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("trigger_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column(
            "trigger_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_feedback_events_user_id",
        "feedback_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_trigger_type",
        "feedback_events",
        ["trigger_type"],
        unique=False,
    )


def downgrade() -> None:
    """Remove optional identity and trigger capture fields."""

    op.drop_index("ix_feedback_events_trigger_type", table_name="feedback_events")
    op.drop_index("ix_feedback_events_user_id", table_name="feedback_events")
    op.drop_column("feedback_events", "trigger_metadata")
    op.drop_column("feedback_events", "trigger_message")
    op.drop_column("feedback_events", "trigger_type")
    op.drop_column("feedback_events", "user_id")
