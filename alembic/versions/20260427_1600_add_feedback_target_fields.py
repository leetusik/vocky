"""add feedback target fields

Revision ID: 20260427_1600
Revises: 20260424_1633
Create Date: 2026-04-27 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_1600"
down_revision: str | None = "20260424_1633"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add optional exact feedback target fields."""

    op.add_column(
        "feedback_events",
        sa.Column("target_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("target_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("target_role", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_events",
        sa.Column("target_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove optional exact feedback target fields."""

    op.drop_column("feedback_events", "target_text")
    op.drop_column("feedback_events", "target_role")
    op.drop_column("feedback_events", "target_id")
    op.drop_column("feedback_events", "target_type")
