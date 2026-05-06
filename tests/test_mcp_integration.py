"""MCP integration tests for capture feedback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest
from mcp import McpError
from mcp.shared.memory import create_connected_server_and_client_session
from sqlalchemy import text

from vocky.capture_queue import CaptureQueue
import vocky.tools.capture_feedback as capture_module
import vocky.tools.list_feedback as list_module
import vocky.tools.list_liked_conversations as liked_module
import vocky.tools.summarize_feedback as summarize_module
from vocky.db import get_engine, get_session_maker
from vocky.feedback import FeedbackService
from vocky.mcp_server import mcp
from vocky.worker import CaptureWorker


@pytest.mark.anyio
async def test_capture_feedback_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(capture_module, "get_capture_queue", lambda: CaptureQueue(redis_client))

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "The export flow is broken",
                "source": {"product": "vocky-cli", "integration": "pytest"},
                "feedback_value": 2,
                "comment": "The answer did not fix export",
                "channel": "web",
                "user_id": "user_123",
                "trigger_type": "dislike",
                "trigger_message": "Thumbs down",
                "trigger_metadata": {"control_id": "assistant-message-1-downvote"},
                "target_type": "message",
                "target_id": "assistant-message-1",
                "target_role": "assistant",
                "target_text": "Click export",
                "event_at": "2026-04-23T14:00:00+09:00",
                "tags": ["billing", " bug "],
                "messages": [
                    {"role": "user", "content": "Export billing data"},
                    {"role": "assistant", "content": "Click export"},
                ],
                "used_context": [{"source": "billing-doc", "snippet": "Export steps"}],
                "source_metadata": {"channel": "pytest"},
                "attributes": {"priority": "high"},
            },
        )

    assert result.isError is False
    assert result.structuredContent is not None
    assert set(result.structuredContent) == {"request_id", "accepted_at", "status"}
    assert result.structuredContent["status"] == "accepted"
    assert await redis_client.llen("vocky:capture:feedback") == 1

    queued_job = await CaptureQueue(redis_client).pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.feedback_value == 2
    assert queued_job.payload.comment == "The answer did not fix export"
    assert queued_job.payload.channel == "web"
    assert queued_job.payload.user_id == "user_123"
    assert queued_job.payload.trigger_type == "dislike"
    assert queued_job.payload.trigger_message == "Thumbs down"
    assert queued_job.payload.trigger_metadata == {"control_id": "assistant-message-1-downvote"}
    assert queued_job.payload.target_type == "message"
    assert queued_job.payload.target_id == "assistant-message-1"
    assert queued_job.payload.target_role == "assistant"
    assert queued_job.payload.target_text == "Click export"
    assert queued_job.payload.event_at == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)
    assert queued_job.payload.tags == ("billing", "bug")
    assert queued_job.payload.messages == (
        {"role": "user", "content": "Export billing data"},
        {"role": "assistant", "content": "Click export"},
    )
    assert queued_job.payload.used_context == (
        {"source": "billing-doc", "snippet": "Export steps"},
    )
    assert queued_job.payload.source_metadata == {"channel": "pytest"}
    assert queued_job.payload.attributes == {"priority": "high"}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_capture_feedback_validation_error() -> None:
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
async def test_capture_feedback_invalid_channel_returns_tool_error() -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Invalid channel",
                "source": {"product": "vocky-cli"},
                "channel": "email",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "channel must be one of: web, mobile, support"


@pytest.mark.anyio
async def test_capture_feedback_invalid_trigger_type_returns_tool_error() -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Invalid trigger",
                "source": {"product": "vocky-cli"},
                "trigger_type": "thumbs-up",
            },
        )

    assert result.isError is True
    assert result.content[0].text == (
        "trigger_type must be one of: like, dislike, comment, rating, survey, manual, other"
    )


@pytest.mark.anyio
async def test_capture_feedback_invalid_trigger_metadata_returns_tool_error() -> None:
    result = await capture_module.capture_feedback(
        message="Invalid trigger metadata",
        source=capture_module.CaptureFeedbackSourceInput(product="vocky-cli"),
        trigger_metadata=["not", "object"],
    )

    assert result.isError is True
    assert result.content[0].text == "trigger_metadata must be a JSON object"


@pytest.mark.anyio
async def test_capture_feedback_missing_source_product_is_error() -> None:
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
async def test_capture_feedback_queue_failure_returns_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenQueue:
        async def enqueue_feedback(self, payload):
            raise capture_module.CaptureQueueError("boom")

    monkeypatch.setattr(capture_module, "get_capture_queue", lambda: BrokenQueue())

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Storage failure",
                "source": {"product": "vocky-cli"},
            },
        )

    assert result.isError is True
    assert result.content[0].text == "capture queue unavailable"


@pytest.mark.anyio
async def test_capture_feedback_becomes_queryable_after_worker_processing(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    worker = CaptureWorker(
        queue=queue,
        feedback_service=FeedbackService(get_session_maker()),
    )
    monkeypatch.setattr(capture_module, "get_capture_queue", lambda: queue)

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        capture_result = await client_session.call_tool(
            "capture_feedback",
            {
                "message": "Async capture should not block clients",
                "source": {"product": "vocky-cli", "integration": "pytest"},
                "session_id": "async-flow",
                "target_type": "message",
                "target_id": "assistant-async",
                "target_role": "assistant",
                "target_text": "Async capture response",
                "tags": ["async"],
            },
        )

        assert capture_result.isError is False
        accepted_at = datetime.fromisoformat(
            capture_result.structuredContent["accepted_at"].replace("Z", "+00:00")
        ).astimezone(UTC)

        pre_worker_list = await client_session.call_tool(
            "list_feedback",
            {
                "source_product": "vocky-cli",
                "session_id": "async-flow",
            },
        )
        assert pre_worker_list.isError is False
        assert pre_worker_list.structuredContent["records"] == []

        assert await worker.process_next_job(timeout_seconds=1) is True

        post_worker_list = await client_session.call_tool(
            "list_feedback",
            {
                "source_product": "vocky-cli",
                "session_id": "async-flow",
            },
        )
        assert post_worker_list.isError is False
        assert [record["message"] for record in post_worker_list.structuredContent["records"]] == [
            "Async capture should not block clients"
        ]
        persisted_record = post_worker_list.structuredContent["records"][0]
        assert persisted_record["target_type"] == "message"
        assert persisted_record["target_id"] == "assistant-async"
        assert persisted_record["target_role"] == "assistant"
        assert persisted_record["target_text"] == "Async capture response"

        summary_result = await client_session.call_tool(
            "summarize_feedback",
            {
                "start_ingested_at": accepted_at.isoformat().replace("+00:00", "Z"),
                "end_ingested_at": (accepted_at + timedelta(minutes=5))
                .isoformat()
                .replace("+00:00", "Z"),
                "source_product": "vocky-cli",
                "session_id": "async-flow",
                "tag": "async",
            },
        )
        assert summary_result.isError is False
        assert summary_result.structuredContent["total_count"] == 1

    await redis_client.aclose()


@pytest.mark.anyio
async def test_list_feedback_success_returns_records_and_next_cursor(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, user_id, trigger_type, trigger_message, trigger_metadata, "
                "target_type, target_id, target_role, target_text, "
                "feedback_value, comment, channel, event_at, ingested_at, "
                "tags, messages, used_context, source_metadata, attributes"
                ") VALUES "
                "(:id1, :message1, :source_product1, :source_integration1, :conversation_id1, "
                ":session_id1, :user_id1, :trigger_type1, :trigger_message1, "
                "CAST(:trigger_metadata1 AS jsonb), :target_type1, :target_id1, "
                ":target_role1, :target_text1, "
                ":feedback_value1, :comment1, :channel1, "
                ":event_at1, :ingested_at1, :tags1, "
                "CAST(:messages1 AS jsonb), CAST(:used_context1 AS jsonb), "
                "CAST(:source_metadata1 AS jsonb), CAST(:attributes1 AS jsonb)), "
                "(:id2, :message2, :source_product2, :source_integration2, :conversation_id2, "
                ":session_id2, :user_id2, :trigger_type2, :trigger_message2, "
                "CAST(:trigger_metadata2 AS jsonb), :target_type2, :target_id2, "
                ":target_role2, :target_text2, "
                ":feedback_value2, :comment2, :channel2, "
                ":event_at2, :ingested_at2, :tags2, "
                "CAST(:messages2 AS jsonb), CAST(:used_context2 AS jsonb), "
                "CAST(:source_metadata2 AS jsonb), CAST(:attributes2 AS jsonb))"
            ),
            {
                "id1": "00000000-0000-0000-0000-000000000021",
                "message1": "older feedback",
                "source_product1": "vocky-cli",
                "source_integration1": "pytest",
                "conversation_id1": "conv-1",
                "session_id1": "sess-1",
                "user_id1": "user-2",
                "trigger_type1": "like",
                "trigger_message1": "Thumbs up",
                "trigger_metadata1": "{\"control_id\": \"older-like\"}",
                "target_type1": None,
                "target_id1": None,
                "target_role1": None,
                "target_text1": None,
                "feedback_value1": 1,
                "comment1": "older comment",
                "channel1": "web",
                "event_at1": datetime(2026, 4, 23, 0, 0, tzinfo=UTC),
                "ingested_at1": datetime(2026, 4, 23, 0, 1, tzinfo=UTC),
                "tags1": ["bug"],
                "messages1": "[{\"role\": \"user\", \"content\": \"older\"}]",
                "used_context1": "[{\"source\": \"doc-old\"}]",
                "source_metadata1": "{}",
                "attributes1": "{}",
                "id2": "00000000-0000-0000-0000-000000000022",
                "message2": "newer feedback",
                "source_product2": "vocky-cli",
                "source_integration2": "pytest",
                "conversation_id2": "conv-1",
                "session_id2": "sess-1",
                "user_id2": "user-2",
                "trigger_type2": "like",
                "trigger_message2": "Helpful answer",
                "trigger_metadata2": "{\"control_id\": \"newer-like\"}",
                "target_type2": "message",
                "target_id2": "assistant-message-2",
                "target_role2": "assistant",
                "target_text2": "Click export",
                "feedback_value2": 1,
                "comment2": "newer comment",
                "channel2": "web",
                "event_at2": datetime(2026, 4, 23, 0, 2, tzinfo=UTC),
                "ingested_at2": datetime(2026, 4, 23, 0, 3, tzinfo=UTC),
                "tags2": ["bug", "billing"],
                "messages2": "[{\"role\": \"user\", \"content\": \"newer\"}]",
                "used_context2": "[{\"source\": \"doc-new\"}]",
                "source_metadata2": "{\"channel\": \"pytest\"}",
                "attributes2": "{\"priority\": \"high\"}",
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_feedback",
            {
                "source_product": " vocky-cli ",
                "feedback_value": 1,
                "user_id": " user-2 ",
                "trigger_type": " like ",
                "channel": " web ",
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
    assert result.structuredContent["records"][0]["feedback_value"] == 1
    assert result.structuredContent["records"][0]["comment"] == "newer comment"
    assert result.structuredContent["records"][0]["channel"] == "web"
    assert result.structuredContent["records"][0]["user_id"] == "user-2"
    assert result.structuredContent["records"][0]["trigger_type"] == "like"
    assert result.structuredContent["records"][0]["trigger_message"] == "Helpful answer"
    assert result.structuredContent["records"][0]["trigger_metadata"] == {
        "control_id": "newer-like"
    }
    assert result.structuredContent["records"][0]["target_type"] == "message"
    assert result.structuredContent["records"][0]["target_id"] == "assistant-message-2"
    assert result.structuredContent["records"][0]["target_role"] == "assistant"
    assert result.structuredContent["records"][0]["target_text"] == "Click export"
    assert result.structuredContent["records"][0]["messages"] == [
        {"role": "user", "content": "newer"}
    ]
    assert result.structuredContent["records"][0]["used_context"] == [
        {"source": "doc-new"}
    ]
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
        invalid_target_type_result = await client_session.call_tool(
            "list_feedback",
            {
                "target_type": "answer",
            },
        )
        invalid_trigger_type_result = await client_session.call_tool(
            "list_feedback",
            {
                "trigger_type": "thumbs-up",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "tag must not be blank"
    assert invalid_target_type_result.isError is True
    assert invalid_target_type_result.content[0].text == (
        "target_type must be one of: message, conversation, surface"
    )
    assert invalid_trigger_type_result.isError is True
    assert invalid_trigger_type_result.content[0].text == (
        "trigger_type must be one of: like, dislike, comment, rating, survey, manual, other"
    )


@pytest.mark.anyio
async def test_list_feedback_filters_by_target_type(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, target_type, ingested_at"
                ") VALUES "
                "(:null_id, :null_message, :product, NULL, :null_ingested_at), "
                "(:message_id, :message_message, :product, 'message', :message_ingested_at), "
                "(:surface_id, :surface_message, :product, 'surface', :surface_ingested_at)"
            ),
            {
                "null_id": "00000000-0000-0000-0000-0000000000e1",
                "null_message": "legacy null target",
                "message_id": "00000000-0000-0000-0000-0000000000e2",
                "message_message": "message feedback",
                "surface_id": "00000000-0000-0000-0000-0000000000e3",
                "surface_message": "surface feedback",
                "product": "vocky-cli",
                "null_ingested_at": datetime(2026, 4, 23, 0, 1, tzinfo=UTC),
                "message_ingested_at": datetime(2026, 4, 23, 0, 2, tzinfo=UTC),
                "surface_ingested_at": datetime(2026, 4, 23, 0, 3, tzinfo=UTC),
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_feedback",
            {
                "source_product": "vocky-cli",
                "target_type": " message ",
            },
        )

    assert result.isError is False
    assert [record["message"] for record in result.structuredContent["records"]] == [
        "message feedback"
    ]


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
                "session_id, feedback_value, channel, event_at, ingested_at, "
                "tags, source_metadata, attributes"
                ") VALUES "
                "(:id1, :message1, :source_product1, :source_integration1, :conversation_id1, "
                ":session_id1, :feedback_value1, :channel1, :event_at1, :ingested_at1, :tags1, "
                "CAST(:source_metadata1 AS jsonb), CAST(:attributes1 AS jsonb)), "
                "(:id2, :message2, :source_product2, :source_integration2, :conversation_id2, "
                ":session_id2, :feedback_value2, :channel2, :event_at2, :ingested_at2, :tags2, "
                "CAST(:source_metadata2 AS jsonb), CAST(:attributes2 AS jsonb))"
            ),
            {
                "id1": "00000000-0000-0000-0000-000000000041",
                "message1": "older feedback",
                "source_product1": "vocky-cli",
                "source_integration1": "pytest",
                "conversation_id1": "conv-1",
                "session_id1": "sess-1",
                "feedback_value1": 2,
                "channel1": "web",
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
                "feedback_value2": 2,
                "channel2": "web",
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
                "feedback_value": 2,
                "channel": "web",
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
async def test_summarize_feedback_filters_by_target_type(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, user_id, trigger_type, target_type, ingested_at"
                ") VALUES "
                "(:surface_id1, :surface_message1, :product, :user_id, 'survey', "
                "'surface', :surface_ingested_at1), "
                "(:surface_id2, :surface_message2, :product, :user_id, 'survey', "
                "'surface', :surface_ingested_at2), "
                "(:message_id, :message_message, :product, :user_id, 'manual', "
                "'message', :message_ingested_at)"
            ),
            {
                "surface_id1": "00000000-0000-0000-0000-0000000000f1",
                "surface_message1": "surface one",
                "surface_id2": "00000000-0000-0000-0000-0000000000f2",
                "surface_message2": "surface two",
                "message_id": "00000000-0000-0000-0000-0000000000f3",
                "message_message": "message feedback",
                "product": "vocky-cli",
                "user_id": "user-summary",
                "surface_ingested_at1": datetime(2026, 4, 23, 2, 0, tzinfo=UTC),
                "surface_ingested_at2": datetime(2026, 4, 25, 2, 0, tzinfo=UTC),
                "message_ingested_at": datetime(2026, 4, 25, 3, 0, tzinfo=UTC),
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "summarize_feedback",
            {
                "start_ingested_at": "2026-04-23T00:00:00Z",
                "end_ingested_at": "2026-04-26T00:00:00Z",
                "source_product": "vocky-cli",
                "user_id": "user-summary",
                "trigger_type": "survey",
                "target_type": "surface",
            },
        )

    assert result.isError is False
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
        invalid_trigger_type_result = await client_session.call_tool(
            "summarize_feedback",
            {
                "start_ingested_at": "2026-04-23T00:00:00Z",
                "end_ingested_at": "2026-04-24T00:00:00Z",
                "trigger_type": "reaction",
            },
        )

    assert result.isError is True
    assert result.content[0].text == "start_ingested_at is required"
    assert invalid_trigger_type_result.isError is True
    assert invalid_trigger_type_result.content[0].text == (
        "trigger_type must be one of: like, dislike, comment, rating, survey, manual, other"
    )


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
async def test_list_liked_conversations_returns_only_likes_with_context(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, user_id, trigger_type, trigger_message, trigger_metadata, "
                "target_type, target_id, target_role, target_text, "
                "feedback_value, comment, channel, event_at, ingested_at, "
                "tags, messages, used_context, source_metadata, attributes"
                ") VALUES "
                "(:liked_id, :liked_message, :product, :integration, :conversation_id, "
                ":session_id, :user_id, :trigger_type, :trigger_message, "
                "CAST(:trigger_metadata AS jsonb), "
                ":target_type, :target_id, :target_role, :target_text, "
                "1, :liked_comment, :channel, :event_at, :liked_ingested_at, "
                ":liked_tags, CAST(:liked_messages AS jsonb), CAST(:liked_context AS jsonb), "
                "CAST(:liked_metadata AS jsonb), CAST(:liked_attributes AS jsonb)), "
                "(:disliked_id, :disliked_message, :product, :integration, :conversation_id, "
                ":session_id, :user_id, :trigger_type, :trigger_message, "
                "CAST(:trigger_metadata AS jsonb), NULL, NULL, NULL, NULL, "
                "2, :disliked_comment, :channel, :event_at, :disliked_ingested_at, "
                ":disliked_tags, CAST(:disliked_messages AS jsonb), CAST(:disliked_context AS jsonb), "
                "CAST(:disliked_metadata AS jsonb), CAST(:disliked_attributes AS jsonb))"
            ),
            {
                "liked_id": "00000000-0000-0000-0000-000000000061",
                "liked_message": "liked answer",
                "disliked_id": "00000000-0000-0000-0000-000000000062",
                "disliked_message": "disliked answer",
                "product": "agent-product",
                "integration": "pytest",
                "conversation_id": "conv-liked",
                "session_id": "sess-liked",
                "user_id": "user-liked",
                "trigger_type": "like",
                "trigger_message": "Thumbs up",
                "trigger_metadata": "{\"control_id\": \"liked-message-upvote\"}",
                "target_type": "message",
                "target_id": "assistant-liked",
                "target_role": "assistant",
                "target_text": "Use this response pattern",
                "liked_comment": "use this pattern",
                "disliked_comment": "do not use this pattern",
                "channel": "web",
                "event_at": datetime(2026, 4, 24, 1, 0, tzinfo=UTC),
                "liked_ingested_at": datetime(2026, 4, 24, 1, 1, tzinfo=UTC),
                "disliked_ingested_at": datetime(2026, 4, 24, 1, 2, tzinfo=UTC),
                "liked_tags": ["few-shot"],
                "disliked_tags": ["few-shot"],
                "liked_messages": "[{\"role\": \"user\", \"content\": \"How should I respond?\"}]",
                "disliked_messages": "[{\"role\": \"user\", \"content\": \"Bad response\"}]",
                "liked_context": "[{\"source\": \"guide\", \"snippet\": \"Good answer\"}]",
                "disliked_context": "[{\"source\": \"guide\", \"snippet\": \"Bad answer\"}]",
                "liked_metadata": "{\"tenant\": \"test\"}",
                "disliked_metadata": "{\"tenant\": \"test\"}",
                "liked_attributes": "{\"quality\": \"good\"}",
                "disliked_attributes": "{\"quality\": \"bad\"}",
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_liked_conversations",
            {
                "source_product": "agent-product",
                "user_id": "user-liked",
                "trigger_type": "like",
                "channel": "web",
                "tag": "few-shot",
            },
        )

    assert result.isError is False
    assert result.structuredContent is not None
    assert [item["message"] for item in result.structuredContent["conversations"]] == [
        "liked answer"
    ]
    liked = result.structuredContent["conversations"][0]
    assert liked["comment"] == "use this pattern"
    assert liked["user_id"] == "user-liked"
    assert liked["trigger_type"] == "like"
    assert liked["trigger_message"] == "Thumbs up"
    assert liked["trigger_metadata"] == {"control_id": "liked-message-upvote"}
    assert liked["target_type"] == "message"
    assert liked["target_id"] == "assistant-liked"
    assert liked["target_role"] == "assistant"
    assert liked["target_text"] == "Use this response pattern"
    assert liked["messages"] == [
        {"role": "user", "content": "How should I respond?"}
    ]
    assert liked["used_context"] == [
        {"source": "guide", "snippet": "Good answer"}
    ]
    assert liked["attributes"] == {"quality": "good"}


@pytest.mark.anyio
async def test_list_liked_conversations_filters_by_target_type(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, target_type, feedback_value, ingested_at"
                ") VALUES "
                "(:message_id, :message_message, :product, 'message', 1, :message_ingested_at), "
                "(:surface_id, :surface_message, :product, 'surface', 1, :surface_ingested_at), "
                "(:dislike_id, :dislike_message, :product, 'message', 2, :dislike_ingested_at)"
            ),
            {
                "message_id": "00000000-0000-0000-0000-0000000000d1",
                "message_message": "liked message feedback",
                "surface_id": "00000000-0000-0000-0000-0000000000d2",
                "surface_message": "liked surface feedback",
                "dislike_id": "00000000-0000-0000-0000-0000000000d3",
                "dislike_message": "disliked message feedback",
                "product": "agent-product",
                "message_ingested_at": datetime(2026, 4, 24, 1, 0, tzinfo=UTC),
                "surface_ingested_at": datetime(2026, 4, 24, 2, 0, tzinfo=UTC),
                "dislike_ingested_at": datetime(2026, 4, 24, 3, 0, tzinfo=UTC),
            },
        )

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool(
            "list_liked_conversations",
            {
                "source_product": "agent-product",
                "target_type": "message",
            },
        )

    assert result.isError is False
    assert [item["message"] for item in result.structuredContent["conversations"]] == [
        "liked message feedback"
    ]


@pytest.mark.anyio
async def test_list_liked_conversations_storage_failure_returns_tool_error(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenService:
        async def list_feedback(self, query):
            raise liked_module.FeedbackReadError("boom")

    monkeypatch.setattr(liked_module, "get_feedback_service", lambda: BrokenService())

    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        result = await client_session.call_tool("list_liked_conversations", {})

    assert result.isError is True
    assert result.content[0].text == "storage read failed"


@pytest.mark.anyio
async def test_unknown_tool_is_protocol_error(configured_database: str) -> None:
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client_session:
        with pytest.raises(McpError) as exc_info:
            await client_session.call_tool("unknown_tool", {})

    assert exc_info.value.error.code == -32602
    assert exc_info.value.error.message == "Unknown tool: unknown_tool"
