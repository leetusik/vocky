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
    project_id: UUID | None = None
    feedback_value: int | None = None
    comment: str | None = None
    channel: str | None = None
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    trigger_type: str | None = None
    trigger_message: str | None = None
    trigger_metadata: dict[str, Any] = field(default_factory=dict)
    target_type: str | None = None
    target_id: str | None = None
    target_role: str | None = None
    target_text: str | None = None
    event_at: datetime | None = None
    tags: tuple[str, ...] = ()
    messages: tuple[Any, ...] = ()
    used_context: tuple[Any, ...] = ()
    source_metadata: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)
    attachment_ids: tuple[UUID, ...] = ()


@dataclass(slots=True, kw_only=True)
class FeedbackEventRecord:
    """Stored feedback event returned by the service layer."""

    id: UUID
    project_id: UUID | None
    message: str
    source_product: str
    feedback_value: int | None
    comment: str | None
    channel: str | None
    source_integration: str | None
    conversation_id: str | None
    session_id: str | None
    user_id: str | None
    trigger_type: str | None
    trigger_message: str | None
    trigger_metadata: dict[str, Any]
    target_type: str | None
    target_id: str | None
    target_role: str | None
    target_text: str | None
    event_at: datetime | None
    ingested_at: datetime
    tags: tuple[str, ...]
    messages: tuple[Any, ...]
    used_context: tuple[Any, ...]
    source_metadata: dict[str, Any]
    attributes: dict[str, Any]


@dataclass(slots=True, kw_only=True)
class CreateFeedbackComment:
    """Input for storing an operator-authored comment on a feedback event."""

    feedback_id: UUID
    body: str
    author: str | None = None


@dataclass(slots=True, kw_only=True)
class FeedbackCommentRecord:
    """Stored operator comment returned by the service layer."""

    id: UUID
    feedback_id: UUID
    author: str | None
    body: str
    created_at: datetime


@dataclass(slots=True, kw_only=True)
class CreateFeedbackAttachment:
    """Input for storing an uploaded (not-yet-linked) feedback attachment."""

    storage_key: str
    content_type: str
    byte_size: int
    claimed_source_product: str
    claimed_user_id: str | None = None
    filename: str | None = None


@dataclass(slots=True, kw_only=True)
class FeedbackAttachmentRecord:
    """Stored feedback attachment returned by the service layer."""

    id: UUID
    feedback_id: UUID | None
    storage_key: str
    content_type: str
    byte_size: int
    filename: str | None
    claimed_user_id: str | None
    claimed_source_product: str
    created_at: datetime


@dataclass(slots=True, kw_only=True)
class FeedbackQueryFilters:
    """Supported filters for feedback read queries."""

    project_id: UUID | None = None
    project_ids: tuple[UUID, ...] | None = None
    search: str | None = None
    start_ingested_at: datetime | None = None
    end_ingested_at: datetime | None = None
    source_product: str | None = None
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    trigger_type: str | None = None
    feedback_value: int | None = None
    channel: str | None = None
    target_type: str | None = None
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
class FeedbackMetricsQuery:
    """Input for dashboard feedback metrics."""

    filters: FeedbackQueryFilters


@dataclass(slots=True, kw_only=True)
class FeedbackDailyCount:
    """Daily UTC count returned by a feedback summary."""

    day: date
    count: int


@dataclass(slots=True, kw_only=True)
class FeedbackMetricCounts:
    """Feedback value counts for one metrics bucket."""

    total: int
    liked: int
    disliked: int
    unrated: int


@dataclass(slots=True, kw_only=True)
class FeedbackDailyMetricCount:
    """Daily UTC counts returned by dashboard metrics."""

    day: date
    total: int
    liked: int
    disliked: int
    unrated: int


@dataclass(slots=True, kw_only=True)
class FeedbackSummary:
    """Aggregate feedback summary over a requested window."""

    total_count: int
    daily_counts: tuple[FeedbackDailyCount, ...]


@dataclass(slots=True, kw_only=True)
class FeedbackMetrics:
    """Dashboard aggregate feedback metrics over a requested window."""

    totals: FeedbackMetricCounts
    daily_counts: tuple[FeedbackDailyMetricCount, ...]
