"""add feedback trigram search index

Revision ID: 20260716_1600
Revises: 20260716_1500
Create Date: 2026-07-16 16:00:00

Accelerates the multilingual (Korean + English) free-text feedback search
introduced on the ``/app/feedback`` surface. Search is a case-insensitive
substring (``ILIKE``) match over the concatenated user-visible text columns; a
``pg_trgm`` trigram GIN index over that same immutable expression lets the
planner accelerate it. Deliberately **no** ``to_tsvector('english', …)`` — English
stemming is wrong for Korean and Korean 조사/particles defeat word-token matching
(decision D-P3-4). The index expression must byte-for-byte match the predicate in
``vocky.feedback.repository._feedback_search_target`` so the planner can use it.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260716_1600"
down_revision: str | None = "20260716_1500"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Immutable concatenation of the searchable text columns. Kept in lock-step with
# ``vocky.feedback.repository._feedback_search_target`` (the ILIKE predicate).
_SEARCH_EXPR = (
    "coalesce(message, '') || ' ' || "
    "coalesce(comment, '') || ' ' || "
    "coalesce(target_text, '') || ' ' || "
    "coalesce(trigger_message, '')"
)


def upgrade() -> None:
    """Enable ``pg_trgm`` and add the trigram GIN search index."""

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_feedback_events_search_trgm "
        f"ON feedback_events USING gin (({_SEARCH_EXPR}) gin_trgm_ops)"
    )


def downgrade() -> None:
    """Drop the trigram search index (leave the ``pg_trgm`` extension in place)."""

    op.execute("DROP INDEX IF EXISTS ix_feedback_events_search_trgm")
