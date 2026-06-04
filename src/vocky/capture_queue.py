"""Redis-backed capture queue primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from vocky.feedback import CreateFeedbackEvent
from vocky.redis_client import get_redis_client

CAPTURE_QUEUE_KEY = "vocky:capture:feedback"
CAPTURE_DEAD_LETTER_KEY = "vocky:capture:feedback:dead_letter"
CAPTURE_MAX_ATTEMPTS = 3


class CaptureQueueError(RuntimeError):
    """Raised when capture queue operations fail."""


@dataclass(slots=True, kw_only=True)
class AcceptedCaptureJob:
    """Receipt returned when the queue accepts a capture request."""

    request_id: UUID
    accepted_at: datetime


@dataclass(slots=True, kw_only=True)
class CaptureJob:
    """Background job payload stored in Redis."""

    request_id: UUID
    accepted_at: datetime
    payload: CreateFeedbackEvent
    attempt: int = 1


def serialize_datetime(value: datetime) -> str:
    """Serialize a timestamp as UTC ISO 8601."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def deserialize_datetime(value: str) -> datetime:
    """Parse a UTC ISO 8601 timestamp."""

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _serialize_payload(payload: CreateFeedbackEvent) -> dict[str, Any]:
    """Convert a capture payload into a JSON-safe structure."""

    return {
        "message": payload.message,
        "source_product": payload.source_product,
        "feedback_value": payload.feedback_value,
        "comment": payload.comment,
        "channel": payload.channel,
        "source_integration": payload.source_integration,
        "conversation_id": payload.conversation_id,
        "session_id": payload.session_id,
        "user_id": payload.user_id,
        "trigger_type": payload.trigger_type,
        "trigger_message": payload.trigger_message,
        "trigger_metadata": dict(payload.trigger_metadata),
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "target_role": payload.target_role,
        "target_text": payload.target_text,
        "event_at": (
            serialize_datetime(payload.event_at)
            if payload.event_at is not None
            else None
        ),
        "tags": list(payload.tags),
        "messages": list(payload.messages),
        "used_context": list(payload.used_context),
        "source_metadata": dict(payload.source_metadata),
        "attributes": dict(payload.attributes),
        "attachment_ids": [str(attachment_id) for attachment_id in payload.attachment_ids],
    }


def _deserialize_payload(raw: dict[str, Any]) -> CreateFeedbackEvent:
    """Convert a JSON payload into the transport-neutral capture input."""

    return CreateFeedbackEvent(
        message=str(raw["message"]),
        source_product=str(raw["source_product"]),
        feedback_value=(
            int(raw["feedback_value"])
            if raw.get("feedback_value") is not None
            else None
        ),
        comment=(
            str(raw["comment"])
            if raw.get("comment") is not None
            else None
        ),
        channel=(
            str(raw["channel"])
            if raw.get("channel") is not None
            else None
        ),
        source_integration=(
            str(raw["source_integration"])
            if raw.get("source_integration") is not None
            else None
        ),
        conversation_id=(
            str(raw["conversation_id"])
            if raw.get("conversation_id") is not None
            else None
        ),
        session_id=(
            str(raw["session_id"])
            if raw.get("session_id") is not None
            else None
        ),
        user_id=(
            str(raw["user_id"])
            if raw.get("user_id") is not None
            else None
        ),
        trigger_type=(
            str(raw["trigger_type"])
            if raw.get("trigger_type") is not None
            else None
        ),
        trigger_message=(
            str(raw["trigger_message"])
            if raw.get("trigger_message") is not None
            else None
        ),
        trigger_metadata=dict(raw.get("trigger_metadata") or {}),
        target_type=(
            str(raw["target_type"])
            if raw.get("target_type") is not None
            else None
        ),
        target_id=(
            str(raw["target_id"])
            if raw.get("target_id") is not None
            else None
        ),
        target_role=(
            str(raw["target_role"])
            if raw.get("target_role") is not None
            else None
        ),
        target_text=(
            str(raw["target_text"])
            if raw.get("target_text") is not None
            else None
        ),
        event_at=(
            deserialize_datetime(str(raw["event_at"]))
            if raw.get("event_at") is not None
            else None
        ),
        tags=tuple(str(tag) for tag in raw.get("tags", [])),
        messages=tuple(raw.get("messages", [])),
        used_context=tuple(raw.get("used_context", [])),
        source_metadata=dict(raw.get("source_metadata", {})),
        attributes=dict(raw.get("attributes", {})),
        attachment_ids=tuple(
            UUID(str(attachment_id)) for attachment_id in raw.get("attachment_ids", [])
        ),
    )


def serialize_job(job: CaptureJob) -> str:
    """Serialize a capture job for Redis storage."""

    return json.dumps(
        {
            "request_id": str(job.request_id),
            "accepted_at": serialize_datetime(job.accepted_at),
            "attempt": job.attempt,
            "payload": _serialize_payload(job.payload),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def deserialize_job(raw: str) -> CaptureJob:
    """Deserialize a capture job from Redis storage."""

    payload = json.loads(raw)
    return CaptureJob(
        request_id=UUID(str(payload["request_id"])),
        accepted_at=deserialize_datetime(str(payload["accepted_at"])),
        attempt=int(payload["attempt"]),
        payload=_deserialize_payload(dict(payload["payload"])),
    )


class CaptureQueue:
    """Redis-backed queue for accepted capture jobs."""

    def __init__(
        self,
        redis_client: Redis,
        *,
        queue_key: str = CAPTURE_QUEUE_KEY,
        dead_letter_key: str = CAPTURE_DEAD_LETTER_KEY,
    ) -> None:
        self._redis_client = redis_client
        self.queue_key = queue_key
        self.dead_letter_key = dead_letter_key

    async def enqueue_feedback(
        self,
        payload: CreateFeedbackEvent,
    ) -> AcceptedCaptureJob:
        """Queue a newly accepted feedback payload and return its receipt."""

        receipt = AcceptedCaptureJob(
            request_id=uuid4(),
            accepted_at=datetime.now(UTC),
        )
        await self.requeue_job(
            CaptureJob(
                request_id=receipt.request_id,
                accepted_at=receipt.accepted_at,
                payload=payload,
                attempt=1,
            )
        )
        return receipt

    async def requeue_job(self, job: CaptureJob) -> None:
        """Push a capture job onto the processing queue."""

        try:
            await self._redis_client.rpush(self.queue_key, serialize_job(job))
        except RedisError as exc:
            raise CaptureQueueError("failed to enqueue capture job") from exc

    async def pop_job(self, *, timeout_seconds: int = 1) -> CaptureJob | None:
        """Pop the next capture job, waiting up to the provided timeout."""

        try:
            result = await self._redis_client.blpop(self.queue_key, timeout=timeout_seconds)
        except RedisError as exc:
            raise CaptureQueueError("failed to read capture job") from exc

        if result is None:
            return None

        _, raw_job = result
        try:
            return deserialize_job(raw_job)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CaptureQueueError("failed to decode capture job") from exc

    async def dead_letter_job(self, job: CaptureJob, *, error_message: str) -> None:
        """Store a permanently failed job in the dead-letter list."""

        payload = json.dumps(
            {
                "request_id": str(job.request_id),
                "accepted_at": serialize_datetime(job.accepted_at),
                "attempt": job.attempt,
                "payload": _serialize_payload(job.payload),
                "failed_at": serialize_datetime(datetime.now(UTC)),
                "error_message": error_message,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

        try:
            await self._redis_client.rpush(self.dead_letter_key, payload)
        except RedisError as exc:
            raise CaptureQueueError("failed to dead-letter capture job") from exc


def get_capture_queue() -> CaptureQueue:
    """Return the shared capture queue facade."""

    return CaptureQueue(get_redis_client())
