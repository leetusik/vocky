"""Capture feedback MCP tool (write-only, per-project ``vk_`` authenticated)."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent

from vocky.auth import get_request_credential
from vocky.capture import (
    CaptureFeedbackSourceInput,
    CaptureFeedbackValidationError,
    McpCaptureFeedbackInput,
    normalize_mcp_payload,
    serialize_capture_receipt,
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
    user_id: str | None = None,
    trigger_type: str | None = None,
    trigger_message: str | None = None,
    trigger_metadata: dict[str, Any] | None = None,
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
    ctx: Context | None = None,
) -> CallToolResult:
    """Capture a single feedback event for later review.

    The event is scoped to the project of the per-project ``vk_`` credential the
    MCP transport authenticated: the credential the ingest middleware stashed on
    the ASGI scope is read back off ``ctx.request_context.request`` and its
    ``project_id`` is stamped onto the payload before enqueue.
    """

    raw_payload = McpCaptureFeedbackInput(
        message=message,
        source=source,
        feedback_value=feedback_value,
        comment=comment,
        channel=channel,
        conversation_id=conversation_id,
        session_id=session_id,
        user_id=user_id,
        trigger_type=trigger_type,
        trigger_message=trigger_message,
        trigger_metadata=trigger_metadata,
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
        normalized = normalize_mcp_payload(raw_payload)
    except CaptureFeedbackValidationError as exc:
        return error_result(str(exc))

    # The transport is guarded by ``ProjectCredentialAuthMiddleware`` (whole
    # ``/mcp`` endpoint), so a request always carries a resolved credential; the
    # None guards are defensive and should never trigger in practice.
    request = ctx.request_context.request if ctx is not None else None
    if request is None:
        return error_result("capture feedback is not available for this request")

    normalized.payload.project_id = get_request_credential(request).project_id

    try:
        receipt = await get_capture_queue().enqueue_feedback(normalized.payload)
    except CaptureQueueError:
        logger.exception("Failed to enqueue captured feedback event")
        return error_result("capture queue unavailable")

    response = serialize_capture_receipt(
        request_id=receipt.request_id,
        accepted_at=receipt.accepted_at,
    )

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Accepted feedback capture {response.request_id}",
            )
        ],
        structuredContent=response.model_dump(mode="json"),
        isError=False,
    )
