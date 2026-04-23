"""Transport-neutral feedback data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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
