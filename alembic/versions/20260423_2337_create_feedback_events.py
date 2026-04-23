"""create feedback_events

Revision ID: 20260423_2337
Revises:
Create Date: 2026-04-23 23:37:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260423_2337"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the feedback_events table and its indexes."""

    op.create_table(
        "feedback_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_product", sa.Text(), nullable=False),
        sa.Column("source_integration", sa.Text(), nullable=True),
        sa.Column("conversation_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback_events")),
    )
    op.create_index(
        "ix_feedback_events_ingested_at",
        "feedback_events",
        ["ingested_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_event_at",
        "feedback_events",
        ["event_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_source_product",
        "feedback_events",
        ["source_product"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_conversation_id",
        "feedback_events",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_session_id",
        "feedback_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_events_tags_gin",
        "feedback_events",
        ["tags"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop the feedback_events table and its indexes."""

    op.drop_index("ix_feedback_events_tags_gin", table_name="feedback_events")
    op.drop_index("ix_feedback_events_session_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_conversation_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_source_product", table_name="feedback_events")
    op.drop_index("ix_feedback_events_event_at", table_name="feedback_events")
    op.drop_index("ix_feedback_events_ingested_at", table_name="feedback_events")
    op.drop_table("feedback_events")
