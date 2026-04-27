"""Capture feedback MCP tool."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from vocky.capture import (
    CaptureFeedbackInput,
    CaptureFeedbackSourceInput,
    CaptureFeedbackValidationError,
    serialize_capture_receipt,
    normalize_payload,
)
from vocky.capture_queue import CaptureQueueError, get_capture_queue
from vocky.mcp_server import mcp

logger = logging.getLogger(__name__)


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
    feedback_value: int | None = None,
    comment: str | None = None,
    channel: str | None = None,
    conversation_id: str | None = None,
    session_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    target_role: str | None = None,
    target_text: str | None = None,
    event_at: str | None = None,
    tags: list[str] | None = None,
    messages: list[Any] | None = None,
    used_context: list[Any] | None = None,
    source_metadata: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> CallToolResult:
    """Capture a single feedback event for later review."""

    raw_payload = CaptureFeedbackInput(
        message=message,
        source=source,
        feedback_value=feedback_value,
        comment=comment,
        channel=channel,
        conversation_id=conversation_id,
        session_id=session_id,
        target_type=target_type,
        target_id=target_id,
        target_role=target_role,
        target_text=target_text,
        event_at=event_at,
        tags=tags,
        messages=messages,
        used_context=used_context,
        source_metadata=source_metadata or {},
        attributes=attributes or {},
    )

    try:
        normalized = normalize_payload(raw_payload)
    except CaptureFeedbackValidationError as exc:
        return error_result(str(exc))

    try:
        receipt = await get_capture_queue().enqueue_feedback(normalized.payload)
    except CaptureQueueError:
        logger.exception("Failed to enqueue captured feedback event")
        return error_result("capture queue unavailable")

    response = serialize_capture_receipt(
        request_id=receipt.request_id,
        accepted_at=receipt.accepted_at,
    )
    structured_content = response.model_dump(mode="json")

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Accepted feedback capture {response.request_id}",
            )
        ],
        structuredContent=structured_content,
        isError=False,
    )
