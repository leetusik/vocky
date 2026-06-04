"""Tests for the capture worker."""

from __future__ import annotations

from uuid import uuid4

import fakeredis.aioredis
import pytest

from vocky.capture_queue import CaptureQueue
from vocky.db import get_session_maker
from vocky.feedback import (
    CreateFeedbackAttachment,
    CreateFeedbackEvent,
    FeedbackPersistenceError,
    FeedbackService,
)
from vocky.worker import CaptureWorker


class FlakyFeedbackService:
    """Fail once, then succeed."""

    def __init__(self) -> None:
        self.calls = 0

    async def create_feedback_event(self, payload: CreateFeedbackEvent) -> None:
        self.calls += 1
        if self.calls == 1:
            raise FeedbackPersistenceError("temporary failure")


class RecordingFeedbackService:
    """Record which persistence path the worker chose."""

    def __init__(self) -> None:
        self.plain_calls = 0
        self.with_attachments_calls = 0

    async def create_feedback_event(self, payload: CreateFeedbackEvent) -> None:
        self.plain_calls += 1

    async def create_feedback_event_with_attachments(
        self, payload: CreateFeedbackEvent
    ) -> None:
        self.with_attachments_calls += 1


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


@pytest.mark.asyncio
async def test_worker_uses_with_attachments_path_when_ids_present() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = RecordingFeedbackService()
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=3)

    await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="with images",
            source_product="changple5",
            attachment_ids=(uuid4(),),
        )
    )

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert service.with_attachments_calls == 1
    assert service.plain_calls == 0

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_worker_uses_plain_path_when_no_attachment_ids() -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = RecordingFeedbackService()
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=3)

    await queue.enqueue_feedback(
        CreateFeedbackEvent(message="no images", source_product="changple5")
    )

    assert await worker.process_next_job(timeout_seconds=1) is True
    assert service.plain_calls == 1
    assert service.with_attachments_calls == 0

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_worker_links_attachments_on_persist(configured_database: str) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    service = FeedbackService(get_session_maker())
    attachment = await service.create_unlinked_attachment(
        CreateFeedbackAttachment(
            storage_key="worker-key",
            content_type="image/png",
            byte_size=3,
            filename=None,
            claimed_user_id="user-1",
            claimed_source_product="changple5",
        )
    )
    worker = CaptureWorker(queue=queue, feedback_service=service, max_attempts=3)

    await queue.enqueue_feedback(
        CreateFeedbackEvent(
            message="captured with image",
            source_product="changple5",
            user_id="user-1",
            attachment_ids=(attachment.id,),
        )
    )

    assert await worker.process_next_job(timeout_seconds=1) is True
    linked = await service.get_feedback_attachment(attachment.id)
    assert linked is not None
    assert linked.feedback_id is not None

    await redis_client.aclose()
