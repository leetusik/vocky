"""Tests for the Redis-backed capture queue."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import fakeredis.aioredis
import pytest

from vocky.capture_queue import (
    CaptureJob,
    CaptureQueue,
    deserialize_job,
    serialize_datetime,
    serialize_job,
)
from vocky.feedback import CreateFeedbackEvent


@pytest.mark.asyncio
async def test_enqueue_and_pop_round_trip_preserves_payload() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)

    receipt = await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="Need CSV export",
            source_product="vocky-cli",
            feedback_value=1,
            comment="This answer was useful",
            channel="web",
            source_integration="pytest",
            conversation_id="conv-1",
            session_id="sess-1",
            user_id="user-1",
            trigger_type="like",
            trigger_message="Thumbs up",
            trigger_metadata={"control_id": "msg-1-like"},
            target_type="message",
            target_id="msg-1",
            target_role="assistant",
            target_text="Click export",
            event_at=datetime(2026, 4, 24, 2, 30, tzinfo=UTC),
            tags=("feature-request", "export"),
            messages=({"role": "user", "content": "Export this"},),
            used_context=({"source": "export-doc"},),
            source_metadata={"channel": "test"},
            attributes={"priority": "high"},
        )
    )

    job = await queue.pop_job(timeout_seconds=1)

    assert job is not None
    assert job.request_id == receipt.request_id
    assert job.accepted_at == receipt.accepted_at
    assert job.payload.message == "Need CSV export"
    assert job.payload.source_product == "vocky-cli"
    assert job.payload.feedback_value == 1
    assert job.payload.comment == "This answer was useful"
    assert job.payload.channel == "web"
    assert job.payload.source_integration == "pytest"
    assert job.payload.conversation_id == "conv-1"
    assert job.payload.session_id == "sess-1"
    assert job.payload.user_id == "user-1"
    assert job.payload.trigger_type == "like"
    assert job.payload.trigger_message == "Thumbs up"
    assert job.payload.trigger_metadata == {"control_id": "msg-1-like"}
    assert job.payload.target_type == "message"
    assert job.payload.target_id == "msg-1"
    assert job.payload.target_role == "assistant"
    assert job.payload.target_text == "Click export"
    assert job.payload.event_at == datetime(2026, 4, 24, 2, 30, tzinfo=UTC)
    assert job.payload.tags == ("feature-request", "export")
    assert job.payload.messages == ({"role": "user", "content": "Export this"},)
    assert job.payload.used_context == ({"source": "export-doc"},)
    assert job.payload.source_metadata == {"channel": "test"}
    assert job.payload.attributes == {"priority": "high"}
    assert job.payload.attachment_ids == ()

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_queue_round_trip_preserves_attachment_ids() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    first, second = uuid4(), uuid4()

    await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="with images",
            source_product="changple5",
            attachment_ids=(first, second),
        )
    )
    job = await queue.pop_job(timeout_seconds=1)

    assert job is not None
    assert job.payload.attachment_ids == (first, second)

    await redis_client.aclose()


def test_serialize_job_encodes_attachment_ids_as_strings() -> None:
    attachment_id = uuid4()
    job = CaptureJob(
        request_id=uuid4(),
        accepted_at=datetime(2026, 6, 4, tzinfo=UTC),
        payload=CreateFeedbackEvent(
            message="m",
            source_product="p",
            attachment_ids=(attachment_id,),
        ),
    )

    data = json.loads(serialize_job(job))

    assert data["payload"]["attachment_ids"] == [str(attachment_id)]
    assert all(isinstance(value, str) for value in data["payload"]["attachment_ids"])


def test_deserialize_job_defaults_missing_optional_added_fields() -> None:
    raw_job = json.dumps(
        {
            "request_id": str(uuid4()),
            "accepted_at": serialize_datetime(datetime(2026, 4, 24, 2, 30, tzinfo=UTC)),
            "attempt": 1,
            "payload": {
                "message": "Legacy queued job",
                "source_product": "vocky-cli",
                "feedback_value": None,
                "comment": None,
                "channel": None,
                "source_integration": None,
                "conversation_id": None,
                "session_id": None,
                "event_at": None,
                "tags": [],
                "messages": [],
                "used_context": [],
                "source_metadata": {},
                "attributes": {},
            },
        },
        separators=(",", ":"),
    )

    job = deserialize_job(raw_job)

    assert job.payload.target_type is None
    assert job.payload.target_id is None
    assert job.payload.target_role is None
    assert job.payload.target_text is None
    assert job.payload.user_id is None
    assert job.payload.trigger_type is None
    assert job.payload.trigger_message is None
    assert job.payload.trigger_metadata == {}
    # A job serialized before attachments existed deserializes to no attachments.
    assert job.payload.attachment_ids == ()


@pytest.mark.asyncio
async def test_dead_letter_job_records_failure_context() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    receipt = await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="Need stronger retries",
            source_product="vocky-cli",
        )
    )
    job = await queue.pop_job(timeout_seconds=1)
    assert job is not None

    await queue.dead_letter_job(job, error_message="storage write failed")

    dead_letters = await redis_client.lrange(queue.dead_letter_key, 0, -1)
    assert len(dead_letters) == 1
    assert str(receipt.request_id) in dead_letters[0]
    assert "storage write failed" in dead_letters[0]

    await redis_client.aclose()
