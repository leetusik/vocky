"""MCP integration tests for capture feedback."""

from __future__ import annotations

import pytest
from mcp import McpError
from mcp.shared.memory import create_connected_server_and_client_session

import vocky.tools.capture_feedback as capture_module
from vocky.feedback import FeedbackPersistenceError
from vocky.mcp_server import mcp


@pytest.mark.anyio
async def test_capture_feedback_success(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "The export flow is broken",
                "source": {"product": "vocky-cli", "integration": "pytest"},
                "event_at": "2026-04-23T14:00:00+09:00",
                "tags": ["billing", " bug "],
                "source_metadata": {"channel": "pytest"},
                "attributes": {"priority": "high"},
            },
        )

    assert result.isError is False
    assert result.structuredContent is not None
    assert set(result.structuredContent) == {"feedback_id", "ingested_at", "event_at"}
    assert result.structuredContent["event_at"] == "2026-04-23T05:00:00Z"


@pytest.mark.anyio
async def test_capture_feedback_validation_error(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "   ",
                "source": {"product": "vocky-cli"},
            },
        )

    assert result.isError is True
    assert result.content[0].text == "message must not be blank"


@pytest.mark.anyio
async def test_capture_feedback_missing_source_product_is_error(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Missing source product",
                "source": {},
            },
        )

    assert result.isError is True
    assert "Field required" in result.content[0].text


@pytest.mark.anyio
async def test_capture_feedback_storage_failure_returns_tool_error(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenService:
        async def create_feedback_event(self, payload):
            raise FeedbackPersistenceError("boom")

    monkeypatch.setattr(capture_module, "get_feedback_service", lambda: BrokenService())

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Storage failure",
                "source": {"product": "vocky-cli"},
            },
        )

    assert result.isError is True
    assert result.content[0].text == "storage write failed"


@pytest.mark.anyio
async def test_unknown_tool_is_protocol_error(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        with pytest.raises(McpError) as exc_info:
            await client_session.call_tool("unknown_tool", {})

    assert exc_info.value.error.code == -32602
    assert exc_info.value.error.message == "Unknown tool: unknown_tool"
