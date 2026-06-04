"""Background worker for accepted capture jobs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from vocky.capture_queue import (
    CAPTURE_MAX_ATTEMPTS,
    CaptureJob,
    CaptureQueue,
    CaptureQueueError,
    get_capture_queue,
)
from vocky.config import get_settings
from vocky.db import dispose_engine
from vocky.feedback import FeedbackPersistenceError, FeedbackService, get_feedback_service
from vocky.logging import configure_logging
from vocky.redis_client import dispose_redis_client

logger = logging.getLogger(__name__)


class CaptureWorker:
    """Poll capture jobs from Redis and persist them to PostgreSQL."""

    def __init__(
        self,
        *,
        queue: CaptureQueue,
        feedback_service: FeedbackService,
        max_attempts: int = CAPTURE_MAX_ATTEMPTS,
    ) -> None:
        self._queue = queue
        self._feedback_service = feedback_service
        self._max_attempts = max_attempts

    async def process_next_job(self, *, timeout_seconds: int = 1) -> bool:
        """Process one queued capture job if one is available."""

        job = await self._queue.pop_job(timeout_seconds=timeout_seconds)
        if job is None:
            return False

        await self._process_job(job)
        return True

    async def run_forever(self) -> None:
        """Run the worker loop until interrupted."""

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)

        while not stop_event.is_set():
            try:
                await self.process_next_job(timeout_seconds=1)
            except CaptureQueueError:
                logger.exception("Capture queue error in worker loop")
                await asyncio.sleep(1)

    async def _process_job(self, job: CaptureJob) -> None:
        """Persist one queued capture job."""

        try:
            if job.payload.attachment_ids:
                await self._feedback_service.create_feedback_event_with_attachments(
                    job.payload
                )
            else:
                await self._feedback_service.create_feedback_event(job.payload)
        except FeedbackPersistenceError:
            await self._handle_persistence_failure(job)
            return

        logger.info(
            "Persisted accepted capture job %s on attempt %s",
            job.request_id,
            job.attempt,
        )

    async def _handle_persistence_failure(self, job: CaptureJob) -> None:
        """Retry or dead-letter a job whose persistence failed."""

        if job.attempt >= self._max_attempts:
            logger.exception(
                "Capture job %s failed permanently after %s attempt(s)",
                job.request_id,
                job.attempt,
            )
            await self._queue.dead_letter_job(job, error_message="storage write failed")
            return

        logger.exception(
            "Capture job %s failed on attempt %s; requeueing",
            job.request_id,
            job.attempt,
        )
        await self._queue.requeue_job(
            CaptureJob(
                request_id=job.request_id,
                accepted_at=job.accepted_at,
                payload=job.payload,
                attempt=job.attempt + 1,
            )
        )


async def run_worker() -> None:
    """Run the shared capture worker."""

    worker = CaptureWorker(
        queue=get_capture_queue(),
        feedback_service=get_feedback_service(),
    )

    try:
        await worker.run_forever()
    finally:
        await dispose_redis_client()
        await dispose_engine()


def main() -> None:
    """CLI entrypoint for running the Vocky worker."""

    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(run_worker())
