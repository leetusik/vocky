"""List feedback MCP tool."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from mcp.types import CallToolResult, TextContent

from vocky.feedback import (
    FeedbackEventRecord,
    FeedbackQueryFilters,
    FeedbackReadError,
    ListFeedbackQuery,
    get_feedback_service,
)
from vocky.mcp_server import mcp
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    decode_cursor,
    encode_cursor,
    error_result,
    normalize_limit,
    normalize_optional_text,
    normalize_tag,
    parse_timestamp,
    serialize_datetime,
    validate_time_window,
)

logger = logging.getLogger(__name__)


class ListFeedbackInput(BaseModel):
    """Raw MCP tool input for listing feedback."""

    start_ingested_at: str | None = None
    end_ingested_at: str | None = None
    source_product: str | None = None
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    tag: str | None = None
    limit: int | None = None
    cursor: str | None = None


class ListFeedbackRecordResponse(BaseModel):
    """Structured record returned by the listing tool."""

    id: str
    message: str
    source_product: str
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    event_at: str | None = None
    ingested_at: str
    tags: list[str]
    source_metadata: dict[str, Any]
    attributes: dict[str, Any]


class ListFeedbackResponse(BaseModel):
    """Structured MCP success response for feedback listing."""

    records: list[ListFeedbackRecordResponse]
    next_cursor: str | None = None


def normalize_payload(raw: ListFeedbackInput) -> ListFeedbackQuery:
    """Normalize and validate the raw listing payload."""

    start_ingested_at = parse_timestamp(
        raw.start_ingested_at,
        field_name="start_ingested_at",
    )
    end_ingested_at = parse_timestamp(
        raw.end_ingested_at,
        field_name="end_ingested_at",
    )
    validate_time_window(start_ingested_at, end_ingested_at)

    return ListFeedbackQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start_ingested_at,
            end_ingested_at=end_ingested_at,
            source_product=normalize_optional_text(raw.source_product),
            source_integration=normalize_optional_text(raw.source_integration),
            conversation_id=normalize_optional_text(raw.conversation_id),
            session_id=normalize_optional_text(raw.session_id),
            tag=normalize_tag(raw.tag),
        ),
        limit=normalize_limit(raw.limit),
        cursor=decode_cursor(raw.cursor),
    )


def serialize_record(record: FeedbackEventRecord) -> ListFeedbackRecordResponse:
    """Convert a transport-neutral record into the MCP response shape."""

    return ListFeedbackRecordResponse(
        id=str(record.id),
        message=record.message,
        source_product=record.source_product,
        source_integration=record.source_integration,
        conversation_id=record.conversation_id,
        session_id=record.session_id,
        event_at=(
            serialize_datetime(record.event_at)
            if record.event_at is not None
            else None
        ),
        ingested_at=serialize_datetime(record.ingested_at),
        tags=list(record.tags),
        source_metadata=dict(record.source_metadata),
        attributes=dict(record.attributes),
    )


@mcp.tool(name="list_feedback")
async def list_feedback(
    start_ingested_at: str | None = None,
    end_ingested_at: str | None = None,
    source_product: str | None = None,
    source_integration: str | None = None,
    conversation_id: str | None = None,
    session_id: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    cursor: str | None = None,
) -> CallToolResult:
    """List stored feedback records with cursor pagination."""

    raw_payload = ListFeedbackInput(
        start_ingested_at=start_ingested_at,
        end_ingested_at=end_ingested_at,
        source_product=source_product,
        source_integration=source_integration,
        conversation_id=conversation_id,
        session_id=session_id,
        tag=tag,
        limit=limit,
        cursor=cursor,
    )

    try:
        normalized = normalize_payload(raw_payload)
    except FeedbackQueryValidationError as exc:
        return error_result(str(exc))

    try:
        page = await get_feedback_service().list_feedback(normalized)
    except FeedbackReadError:
        logger.exception("Failed to list feedback records")
        return error_result("storage read failed")

    response = ListFeedbackResponse(
        records=[serialize_record(record) for record in page.records],
        next_cursor=(
            encode_cursor(page.next_cursor)
            if page.next_cursor is not None
            else None
        ),
    )

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Listed {len(response.records)} feedback records",
            )
        ],
        structuredContent=response.model_dump(mode="json", exclude_none=True),
        isError=False,
    )
