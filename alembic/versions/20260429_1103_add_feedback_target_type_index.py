"""add feedback target type index

Revision ID: 20260429_1103
Revises: 20260427_1600
Create Date: 2026-04-29 11:03:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260429_1103"
down_revision: str | None = "20260427_1600"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add an exact-match index for target-type read filters."""

    op.create_index(
        "ix_feedback_events_target_type",
        "feedback_events",
        ["target_type"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the target-type read-filter index."""

    op.drop_index("ix_feedback_events_target_type", table_name="feedback_events")
