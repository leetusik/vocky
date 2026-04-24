"""MCP integration tests for capture feedback."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from mcp import McpError
from mcp.shared.memory import create_connected_server_and_client_session
from sqlalchemy import text

import vocky.tools.capture_feedback as capture_module
import vocky.tools.list_feedback as list_module
import vocky.tools.summarize_feedback as summarize_module
from vocky.feedback import FeedbackPersistenceError
from vocky.db import get_engine
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
async def test_list_feedback_success_returns_records_and_next_cursor(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                ") VALUES "
                "(:id1, :message1, :source_product1, :source_integration1, :conversation_id1, "
                ":session_id1, :event_at1, :ingested_at1, :tags1, "
                "CAST(:source_metadata1 AS jsonb), CAST(:attributes1 AS jsonb)), "
                "(:id2, :message2, :source_product2, :source_integration2, :conversation_id2, "
                ":session_id2, :event_at2, :ingested_at2, :tags2, "
                "CAST(:source_metadata2 AS jsonb), CAST(:attributes2 AS jsonb))"
            ),
            {
                "id1": "00000000-0000-0000-0000-000000000021",
                "message1": "older feedback",
                "source_product1": "vocky-cli",
                "source_integration1": "pytest",
                "conversation_id1": "conv-1",
                "session_id1": "sess-1",
                "event_at1": datetime(2026, 4, 23, 0, 0, tzinfo=UTC),
                "ingested_at1": datetime(2026, 4, 23, 0, 1, tzinfo=UTC),
                "tags1": ["bug"],
                "source_metadata1": "{}",
                "attributes1": "{}",
                "id2": "00000000-0000-0000-0000-000000000022",
                "message2": "newer feedback",
                "source_product2": "vocky-cli",
                "source_integration2": "pytest",
                "conversation_id2": "conv-1",
                "session_id2": "sess-1",
                "event_at2": datetime(2026, 4, 23, 0, 2, tzinfo=UTC),
                "ingested_at2": datetime(2026, 4, 23, 0, 3, tzinfo=UTC),
                "tags2": ["bug", "billing"],
                "source_metadata2": "{\"channel\": \"pytest\"}",
                "attributes2": "{\"priority\": \"high\"}",
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_feedback",
            {
                "source_product": " vocky-cli ",
                "tag": " bug ",
                "limit": 1,
            },
        )

    assert result.isError is False
    assert result.structuredContent is not None
    assert [record["message"] for record in result.structuredContent["records"]] == [
        "newer feedback"
    ]
    assert result.structuredContent["records"][0]["ingested_at"] == "2026-04-23T00:03:00Z"
    assert "next_cursor" in result.structuredContent


@pytest.mark.anyio
async def test_list_feedback_validation_error_returns_tool_error(
    configured_database: str,
) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_feedback",
            {
                "tag": "   ",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "tag must not be blank"


@pytest.mark.anyio
async def test_list_feedback_storage_failure_returns_tool_error(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenService:
        async def list_feedback(self, query):
            raise list_module.FeedbackReadError("boom")

    monkeypatch.setattr(list_module, "get_feedback_service", lambda: BrokenService())

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_feedback",
            {},
        )

    assert result.isError is True
    assert result.content[0].text == "storage read failed"


@pytest.mark.anyio
async def test_summarize_feedback_success_returns_total_and_daily_counts(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                ") VALUES "
                "(:id1, :message1, :source_product1, :source_integration1, :conversation_id1, "
                ":session_id1, :event_at1, :ingested_at1, :tags1, "
                "CAST(:source_metadata1 AS jsonb), CAST(:attributes1 AS jsonb)), "
                "(:id2, :message2, :source_product2, :source_integration2, :conversation_id2, "
                ":session_id2, :event_at2, :ingested_at2, :tags2, "
                "CAST(:source_metadata2 AS jsonb), CAST(:attributes2 AS jsonb))"
            ),
            {
                "id1": "00000000-0000-0000-0000-000000000041",
                "message1": "older feedback",
                "source_product1": "vocky-cli",
                "source_integration1": "pytest",
                "conversation_id1": "conv-1",
                "session_id1": "sess-1",
                "event_at1": None,
                "ingested_at1": datetime(2026, 4, 23, 2, 0, tzinfo=UTC),
                "tags1": ["bug", "billing"],
                "source_metadata1": "{}",
                "attributes1": "{}",
                "id2": "00000000-0000-0000-0000-000000000042",
                "message2": "newer feedback",
                "source_product2": "vocky-cli",
                "source_integration2": "pytest",
                "conversation_id2": "conv-1",
                "session_id2": "sess-1",
                "event_at2": None,
                "ingested_at2": datetime(2026, 4, 25, 6, 0, tzinfo=UTC),
                "tags2": ["billing"],
                "source_metadata2": "{}",
                "attributes2": "{}",
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "summarize_feedback",
            {
                "start_ingested_at": "2026-04-23T00:00:00Z",
                "end_ingested_at": "2026-04-26T00:00:00Z",
                "source_product": "vocky-cli",
                "source_integration": "pytest",
                "conversation_id": "conv-1",
                "session_id": "sess-1",
                "tag": "billing",
            },
        )

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["total_count"] == 2
    assert result.structuredContent["daily_counts"] == [
        {"day": "2026-04-23", "count": 1},
        {"day": "2026-04-24", "count": 0},
        {"day": "2026-04-25", "count": 1},
    ]


@pytest.mark.anyio
async def test_summarize_feedback_validation_error_returns_tool_error(
    configured_database: str,
) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "summarize_feedback",
            {
                "end_ingested_at": "2026-04-24T00:00:00Z",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "start_ingested_at is required"


@pytest.mark.anyio
async def test_summarize_feedback_storage_failure_returns_tool_error(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenService:
        async def summarize_feedback(self, query):
            raise summarize_module.FeedbackReadError("boom")

    monkeypatch.setattr(summarize_module, "get_feedback_service", lambda: BrokenService())

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "summarize_feedback",
            {
                "start_ingested_at": "2026-04-23T00:00:00Z",
                "end_ingested_at": "2026-04-24T00:00:00Z",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "storage read failed"


@pytest.mark.anyio
async def test_unknown_tool_is_protocol_error(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        with pytest.raises(McpError) as exc_info:
            await client_session.call_tool("unknown_tool", {})

    assert exc_info.value.error.code == -32602
    assert exc_info.value.error.message == "Unknown tool: unknown_tool"
