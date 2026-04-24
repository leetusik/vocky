"""Summarize feedback MCP tool."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from mcp.types import CallToolResult, TextContent

from vocky.feedback import (
    FeedbackDailyCount,
    FeedbackQueryFilters,
    FeedbackReadError,
    FeedbackSummary,
    SummarizeFeedbackQuery,
    get_feedback_service,
)
from vocky.mcp_server import mcp
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    error_result,
    normalize_optional_text,
    normalize_tag,
    parse_timestamp,
    validate_time_window,
)

logger = logging.getLogger(__name__)


class SummarizeFeedbackInput(BaseModel):
    """Raw MCP tool input for feedback summaries."""

    start_ingested_at: str | None = None
    end_ingested_at: str | None = None
    source_product: str | None = None
    source_integration: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    tag: str | None = None


class SummarizeFeedbackDailyCountResponse(BaseModel):
    """Structured daily count returned by the summary tool."""

    day: str
    count: int


class SummarizeFeedbackResponse(BaseModel):
    """Structured MCP success response for feedback summaries."""

    total_count: int
    daily_counts: list[SummarizeFeedbackDailyCountResponse]


def normalize_payload(raw: SummarizeFeedbackInput) -> SummarizeFeedbackQuery:
    """Normalize and validate the raw summary payload."""

    start_ingested_at = parse_timestamp(
        raw.start_ingested_at,
        field_name="start_ingested_at",
    )
    if start_ingested_at is None:
        raise FeedbackQueryValidationError("start_ingested_at is required")

    end_ingested_at = parse_timestamp(
        raw.end_ingested_at,
        field_name="end_ingested_at",
    )
    if end_ingested_at is None:
        raise FeedbackQueryValidationError("end_ingested_at is required")

    validate_time_window(start_ingested_at, end_ingested_at)

    return SummarizeFeedbackQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start_ingested_at,
            end_ingested_at=end_ingested_at,
            source_product=normalize_optional_text(raw.source_product),
            source_integration=normalize_optional_text(raw.source_integration),
            conversation_id=normalize_optional_text(raw.conversation_id),
            session_id=normalize_optional_text(raw.session_id),
            tag=normalize_tag(raw.tag),
        )
    )


def serialize_daily_count(
    daily_count: FeedbackDailyCount,
) -> SummarizeFeedbackDailyCountResponse:
    """Convert a transport-neutral daily count into the MCP response shape."""

    return SummarizeFeedbackDailyCountResponse(
        day=daily_count.day.isoformat(),
        count=daily_count.count,
    )


def serialize_summary(summary: FeedbackSummary) -> SummarizeFeedbackResponse:
    """Convert a transport-neutral summary into the MCP response shape."""

    return SummarizeFeedbackResponse(
        total_count=summary.total_count,
        daily_counts=[
            serialize_daily_count(daily_count)
            for daily_count in summary.daily_counts
        ],
    )


@mcp.tool(name="summarize_feedback")
async def summarize_feedback(
    start_ingested_at: str | None = None,
    end_ingested_at: str | None = None,
    source_product: str | None = None,
    source_integration: str | None = None,
    conversation_id: str | None = None,
    session_id: str | None = None,
    tag: str | None = None,
) -> CallToolResult:
    """Summarize stored feedback counts over an ingest-time window."""

    raw_payload = SummarizeFeedbackInput(
        start_ingested_at=start_ingested_at,
        end_ingested_at=end_ingested_at,
        source_product=source_product,
        source_integration=source_integration,
        conversation_id=conversation_id,
        session_id=session_id,
        tag=tag,
    )

    try:
        normalized = normalize_payload(raw_payload)
    except FeedbackQueryValidationError as exc:
        return error_result(str(exc))

    try:
        summary = await get_feedback_service().summarize_feedback(normalized)
    except FeedbackReadError:
        logger.exception("Failed to summarize feedback records")
        return error_result("storage read failed")

    response = serialize_summary(summary)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Summarized {response.total_count} feedback records",
            )
        ],
        structuredContent=response.model_dump(mode="json"),
        isError=False,
    )
