"""Tests for the capture worker."""

from __future__ import annotations

import fakeredis.aioredis
import pytest

from vocky.capture_queue import CaptureQueue
from vocky.feedback import CreateFeedbackEvent, FeedbackPersistenceError
from vocky.worker import CaptureWorker


class FlakyFeedbackService:
    """Fail once, then succeed."""

    def __init__(self) -> None:
        self.calls = 0

    async def create_feedback_event(self, payload: CreateFeedbackEvent) -> None:
        self.calls += 1
        if self.calls == 1:
            raise FeedbackPersistenceError("temporary failure")


class BrokenFeedbackService:
    """Always fail persistence."""

    def __init__(self) -> None:
        self.calls = 0

    async def create_feedback_event(self, payload: CreateFeedbackEvent) -> None:
        self.calls += 1
        raise FeedbackPersistenceError("permanent failure")


@pytest.mark.asyncio
async def test_worker_requeues_then_persists_after_transient_failure() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = FlakyFeedbackService()
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=3)

    await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="Retry me once",
            source_product="vocky-cli",
        )
    )

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert service.calls == 1
    assert await redis_client.llen(queue.queue_key) == 1

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert service.calls == 2
    assert await redis_client.llen(queue.queue_key) == 0
    assert await redis_client.llen(queue.dead_letter_key) == 0

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_worker_dead_letters_after_max_attempts() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = BrokenFeedbackService()
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=2)

    await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="This will fail permanently",
            source_product="vocky-cli",
        )
    )

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert await redis_client.llen(queue.queue_key) == 1
    assert await redis_client.llen(queue.dead_letter_key) == 0

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert service.calls == 2
    assert await redis_client.llen(queue.queue_key) == 0
    assert await redis_client.llen(queue.dead_letter_key) == 1

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_worker_returns_false_when_queue_is_empty() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = BrokenFeedbackService()
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=2)

    assert await worker.process_next_job(timeout_seconds=1) is False

    await redis_client.aclose()
