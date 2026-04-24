"""Tests for the Redis-backed capture queue."""

from __future__ import annotations

from datetime import UTC, datetime

import fakeredis.aioredis
import pytest

from vocky.capture_queue import CaptureQueue
from vocky.feedback import CreateFeedbackEvent


@pytest.mark.asyncio
async def test_enqueue_and_pop_round_trip_preserves_payload() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)

    receipt = await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="Need CSV export",
            source_product="vocky-cli",
            source_integration="pytest",
            conversation_id="conv-1",
            session_id="sess-1",
            event_at=datetime(2026, 4, 24, 2, 30, tzinfo=UTC),
            tags=("feature-request", "export"),
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
    assert job.payload.source_integration == "pytest"
    assert job.payload.conversation_id == "conv-1"
    assert job.payload.session_id == "sess-1"
    assert job.payload.event_at == datetime(2026, 4, 24, 2, 30, tzinfo=UTC)
    assert job.payload.tags == ("feature-request", "export")
    assert job.payload.source_metadata == {"channel": "test"}
    assert job.payload.attributes == {"priority": "high"}

    await redis_client.aclose()


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
