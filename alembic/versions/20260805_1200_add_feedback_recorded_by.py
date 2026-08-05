"""add feedback recorded_by marker

Revision ID: 20260805_1200
Revises: 20260728_1200
Create Date: 2026-08-05 12:00:00

Adds the agent-vs-human capture marker ``feedback_events.recorded_by``
(``agent`` | ``human`` | NULL). Nullable with no backfill and no server default:
every pre-existing row stays NULL, which reads as *unspecified* rather than
*human*. Validation of the two-value vocabulary lives in the application
(``vocky.recorded_by``), matching how ``trigger_type`` and ``channel`` are
handled — no database CHECK constraint, so adding a third actor kind later costs
one constant and no migration.

Deployment ordering is load-bearing: migrate **before** deploying code that reads
the new column. The column is nullable with no backfill, so the migration itself
is instant and non-blocking.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260805_1200"
down_revision: str | None = "20260728_1200"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add the optional recorded_by capture marker and its index."""

    op.add_column(
        "feedback_events",
        sa.Column("recorded_by", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_feedback_events_recorded_by",
        "feedback_events",
        ["recorded_by"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the recorded_by capture marker and its index."""

    op.drop_index("ix_feedback_events_recorded_by", table_name="feedback_events")
    op.drop_column("feedback_events", "recorded_by")
