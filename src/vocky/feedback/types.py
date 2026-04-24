"""Transport-neutral feedback data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True, kw_only=True)
class CreateFeedbackEvent:
    """Input for storing a feedback event."""

    message: str
    source_product: str
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    event_at: datetime | None = None
    tags: tuple[str, ...] = ()
    source_metadata: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class FeedbackEventRecord:
    """Stored feedback event returned by the service layer."""

    id: UUID
    message: str
    source_product: str
    source_integration: str | None
    conversation_id: str | None
    session_id: str | None
    event_at: datetime | None
    ingested_at: datetime
    tags: tuple[str, ...]
    source_metadata: dict[str, Any]
    attributes: dict[str, Any]


@dataclass(slots=True, kw_only=True)
class FeedbackQueryFilters:
    """Supported filters for feedback read queries."""

    start_ingested_at: datetime | None = None
    end_ingested_at: datetime | None = None
    source_product: str | None = None
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    tag: str | None = None


@dataclass(slots=True, kw_only=True)
class FeedbackListCursor:
    """Opaque cursor payload for feedback record pagination."""

    ingested_at: datetime
    id: UUID


@dataclass(slots=True, kw_only=True)
class ListFeedbackQuery:
    """Input for listing stored feedback records."""

    limit: int
    filters: FeedbackQueryFilters = field(default_factory=FeedbackQueryFilters)
    cursor: FeedbackListCursor | None = None


@dataclass(slots=True, kw_only=True)
class FeedbackListPage:
    """A cursor-paginated page of stored feedback records."""

    records: tuple[FeedbackEventRecord, ...]
    next_cursor: FeedbackListCursor | None = None


@dataclass(slots=True, kw_only=True)
class SummarizeFeedbackQuery:
    """Input for summarizing stored feedback records."""

    filters: FeedbackQueryFilters


@dataclass(slots=True, kw_only=True)
class FeedbackDailyCount:
    """Daily UTC count returned by a feedback summary."""

    day: date
    count: int


@dataclass(slots=True, kw_only=True)
class FeedbackSummary:
    """Aggregate feedback summary over a requested window."""

    total_count: int
    daily_counts: tuple[FeedbackDailyCount, ...]
