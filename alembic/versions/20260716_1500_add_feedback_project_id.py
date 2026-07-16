"""add feedback project_id

Revision ID: 20260716_1500
Revises: 20260715_1200
Create Date: 2026-07-16 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260716_1500"
down_revision: str | None = "20260715_1200"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable project scope FK + index to feedback events."""

    op.add_column(
        "feedback_events",
        sa.Column("project_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_feedback_events_project_id_projects",
        "feedback_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_feedback_events_project_id",
        "feedback_events",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the project scope FK + index from feedback events."""

    op.drop_index("ix_feedback_events_project_id", table_name="feedback_events")
    op.drop_constraint(
        "fk_feedback_events_project_id_projects",
        "feedback_events",
        type_="foreignkey",
    )
    op.drop_column("feedback_events", "project_id")
