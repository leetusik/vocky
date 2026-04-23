"""Capture feedback MCP tool."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from mcp.types import CallToolResult, TextContent

from vocky.feedback import CreateFeedbackEvent, FeedbackPersistenceError, get_feedback_service
from vocky.mcp_server import mcp

logger = logging.getLogger(__name__)


class CaptureFeedbackValidationError(ValueError):
    """Raised when the tool input is semantically invalid."""


class CaptureFeedbackSourceInput(BaseModel):
    """Raw nested source input."""

    product: str
    integration: str | None = None


class CaptureFeedbackInput(BaseModel):
    """Raw MCP tool input."""

    message: str
    source: CaptureFeedbackSourceInput
    conversation_id: str | None = None
    session_id: str | None = None
    event_at: str | None = None
    tags: list[str] | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class CaptureFeedbackResponse(BaseModel):
    """Structured MCP success response."""

    feedback_id: str
    ingested_at: str
    event_at: str | None = None


@dataclass(slots=True, kw_only=True)
class NormalizedCaptureFeedback:
    """Normalized tool payload ready for the service layer."""

    payload: CreateFeedbackEvent
    normalized_event_at: datetime | None


def normalize_optional_text(value: str | None) -> str | None:
    """Trim optional text fields and collapse blank values to null."""

    if value is None:
        return None

    trimmed = value.strip()
    return trimmed or None


def require_non_blank(value: str, field_name: str) -> str:
    """Trim a required text field and reject blank values."""

    trimmed = value.strip()
    if not trimmed:
        raise CaptureFeedbackValidationError(f"{field_name} must not be blank")
    return trimmed


def parse_event_at(value: str | None) -> datetime | None:
    """Parse an optional ISO 8601 timestamp and normalize it to UTC."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise CaptureFeedbackValidationError("event_at must not be blank when provided")

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureFeedbackValidationError("event_at must be a valid ISO 8601 timestamp") from exc

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise CaptureFeedbackValidationError("event_at must include a timezone offset")

    return parsed.astimezone(UTC)


def normalize_tags(tags: list[str] | None) -> tuple[str, ...]:
    """Trim tags, reject blanks, and reject duplicates after normalization."""

    if tags is None:
        return ()

    normalized: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        cleaned = tag.strip()
        if not cleaned:
            raise CaptureFeedbackValidationError("tags must not contain blank values")
        if cleaned in seen:
            raise CaptureFeedbackValidationError("tags must not contain duplicates")
        seen.add(cleaned)
        normalized.append(cleaned)

    return tuple(normalized)


def normalize_payload(raw: CaptureFeedbackInput) -> NormalizedCaptureFeedback:
    """Normalize and validate the raw tool payload."""

    normalized_event_at = parse_event_at(raw.event_at)
    payload = CreateFeedbackEvent(
        message=require_non_blank(raw.message, "message"),
        source_product=require_non_blank(raw.source.product, "source.product"),
        source_integration=normalize_optional_text(raw.source.integration),
        conversation_id=normalize_optional_text(raw.conversation_id),
        session_id=normalize_optional_text(raw.session_id),
        event_at=normalized_event_at,
        tags=normalize_tags(raw.tags),
        source_metadata=dict(raw.source_metadata),
        attributes=dict(raw.attributes),
    )
    return NormalizedCaptureFeedback(
        payload=payload,
        normalized_event_at=normalized_event_at,
    )


def serialize_datetime(value: datetime) -> str:
    """Serialize a timestamp as UTC ISO 8601."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def error_result(message: str) -> CallToolResult:
    """Create a tool execution error result."""

    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        isError=True,
    )


@mcp.tool(name="capture_feedback")
async def capture_feedback(
    message: str,
    source: CaptureFeedbackSourceInput,
    conversation_id: str | None = None,
    session_id: str | None = None,
    event_at: str | None = None,
    tags: list[str] | None = None,
    source_metadata: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> CallToolResult:
    """Capture a single feedback event for later review."""

    raw_payload = CaptureFeedbackInput(
        message=message,
        source=source,
        conversation_id=conversation_id,
        session_id=session_id,
        event_at=event_at,
        tags=tags,
        source_metadata=source_metadata or {},
        attributes=attributes or {},
    )

    try:
        normalized = normalize_payload(raw_payload)
    except CaptureFeedbackValidationError as exc:
        return error_result(str(exc))

    try:
        record = await get_feedback_service().create_feedback_event(normalized.payload)
    except FeedbackPersistenceError:
        logger.exception("Failed to persist captured feedback event")
        return error_result("storage write failed")

    response = CaptureFeedbackResponse(
        feedback_id=str(record.id),
        ingested_at=serialize_datetime(record.ingested_at),
        event_at=(
            serialize_datetime(normalized.normalized_event_at)
            if normalized.normalized_event_at is not None
            else None
        ),
    )
    structured_content = response.model_dump(mode="json", exclude_none=True)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Captured feedback {response.feedback_id}",
            )
        ],
        structuredContent=structured_content,
        isError=False,
    )
