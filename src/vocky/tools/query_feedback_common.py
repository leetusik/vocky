"""Shared normalization helpers for feedback read tools."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from uuid import UUID

from vocky.feedback import (
    FeedbackAttachmentRecord,
    FeedbackCommentRecord,
    FeedbackEventRecord,
    FeedbackListCursor,
)
from vocky.recorded_by import RecordedByValidationError, normalize_recorded_by
from vocky.trigger import TriggerTypeValidationError, normalize_trigger_type

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100
ALLOWED_TARGET_TYPES = frozenset({"message", "conversation", "surface"})


class FeedbackQueryValidationError(ValueError):
    """Raised when a feedback read-tool input is semantically invalid."""


def normalize_optional_text(value: str | None) -> str | None:
    """Trim an optional text field and collapse blank values to null."""

    if value is None:
        return None

    trimmed = value.strip()
    return trimmed or None


def normalize_tag(value: str | None) -> str | None:
    """Trim an optional tag and reject blank values."""

    if value is None:
        return None

    trimmed = value.strip()
    if not trimmed:
        raise FeedbackQueryValidationError("tag must not be blank")
    return trimmed


def normalize_feedback_value(value: int | None) -> int | None:
    """Validate an optional explicit action feedback value filter."""

    if value is None:
        return None
    if isinstance(value, bool) or value not in (1, 2):
        raise FeedbackQueryValidationError("feedback_value must be 1 for like or 2 for dislike")
    return value


def normalize_target_type_filter(value: str | None) -> str | None:
    """Normalize and validate an optional target-type read filter."""

    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    if normalized not in ALLOWED_TARGET_TYPES:
        raise FeedbackQueryValidationError(
            "target_type must be one of: message, conversation, surface"
        )
    return normalized


def normalize_trigger_type_filter(value: str | None) -> str | None:
    """Normalize and validate an optional trigger-type read filter."""

    try:
        return normalize_trigger_type(value)
    except TriggerTypeValidationError as exc:
        raise FeedbackQueryValidationError(str(exc)) from exc


def normalize_recorded_by_filter(value: str | None) -> str | None:
    """Normalize and validate an optional recorded-by read filter.

    Delegates to :func:`vocky.recorded_by.normalize_recorded_by` so the read side
    shares one vocabulary (``ALLOWED_RECORDED_BY``) and one error string with the
    capture side. A blank value collapses to *no filter*; ``None`` never means
    "only unspecified rows" — legacy ``NULL`` rows are simply unfilterable, by
    design (the marker is never inferred or backfilled).
    """

    try:
        return normalize_recorded_by(value)
    except RecordedByValidationError as exc:
        raise FeedbackQueryValidationError(str(exc)) from exc


def parse_timestamp(value: str | None, *, field_name: str) -> datetime | None:
    """Parse an optional ISO 8601 timestamp and normalize it to UTC."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise FeedbackQueryValidationError(f"{field_name} must not be blank when provided")

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedbackQueryValidationError(
            f"{field_name} must be a valid ISO 8601 timestamp"
        ) from exc

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise FeedbackQueryValidationError(f"{field_name} must include a timezone offset")

    return parsed.astimezone(UTC)


def validate_time_window(
    start_ingested_at: datetime | None,
    end_ingested_at: datetime | None,
) -> None:
    """Reject invalid ingest-time windows."""

    if (
        start_ingested_at is not None
        and end_ingested_at is not None
        and start_ingested_at >= end_ingested_at
    ):
        raise FeedbackQueryValidationError("start_ingested_at must be before end_ingested_at")


def normalize_limit(value: int | None) -> int:
    """Return a validated list limit or the default page size."""

    if value is None:
        return DEFAULT_LIST_LIMIT

    if value < 1 or value > MAX_LIST_LIMIT:
        raise FeedbackQueryValidationError(f"limit must be between 1 and {MAX_LIST_LIMIT}")

    return value


def parse_int_param(value: str | None, *, field_name: str) -> int | None:
    """Parse an optional integer query parameter."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise FeedbackQueryValidationError(f"{field_name} must not be blank when provided")

    try:
        return int(normalized)
    except ValueError as exc:
        raise FeedbackQueryValidationError(f"{field_name} must be an integer") from exc


def serialize_datetime(value: datetime) -> str:
    """Serialize a timestamp as UTC ISO 8601."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def serialize_record(record: FeedbackEventRecord) -> dict[str, object]:
    """Serialize a feedback record for REST responses.

    Shared by the Admin REST surface and the project-scoped ``/api/*`` review
    surface (and, later, the ``/app/*`` cross-project read) so the record shape
    stays identical across surfaces. ``project_id`` is intentionally omitted: the
    operator/admin surfaces are already global, and the project-scoped caller
    knows its own project from its credential.
    """

    return {
        "id": str(record.id),
        "message": record.message,
        "source_product": record.source_product,
        "feedback_value": record.feedback_value,
        "comment": record.comment,
        "channel": record.channel,
        "source_integration": record.source_integration,
        "recorded_by": record.recorded_by,
        "conversation_id": record.conversation_id,
        "session_id": record.session_id,
        "user_id": record.user_id,
        "trigger_type": record.trigger_type,
        "trigger_message": record.trigger_message,
        "trigger_metadata": dict(record.trigger_metadata),
        "target_type": record.target_type,
        "target_id": record.target_id,
        "target_role": record.target_role,
        "target_text": record.target_text,
        "event_at": (
            serialize_datetime(record.event_at)
            if record.event_at is not None
            else None
        ),
        "ingested_at": serialize_datetime(record.ingested_at),
        "tags": list(record.tags),
        "messages": list(record.messages),
        "used_context": list(record.used_context),
        "source_metadata": dict(record.source_metadata),
        "attributes": dict(record.attributes),
    }


def serialize_comment(comment: FeedbackCommentRecord) -> dict[str, object]:
    """Serialize an operator comment for REST responses.

    Shared by the Admin REST and end-user feedback read surfaces so the comment
    shape stays identical. ``feedback_id`` is omitted because the comment is always
    returned in the context of its parent feedback (URL path or nested record).
    """

    return {
        "id": str(comment.id),
        "author": comment.author,
        "body": comment.body,
        "created_at": serialize_datetime(comment.created_at),
    }


def serialize_attachment(
    attachment: FeedbackAttachmentRecord,
    *,
    url: str,
) -> dict[str, object]:
    """Serialize an attachment's metadata for REST responses.

    Shared by the Admin REST and end-user feedback read surfaces. ``url`` is the
    surface-specific relative download path the caller builds, because the
    operator and end-user download routes live under different path prefixes.
    """

    return {
        "id": str(attachment.id),
        "content_type": attachment.content_type,
        "byte_size": attachment.byte_size,
        "filename": attachment.filename,
        "created_at": serialize_datetime(attachment.created_at),
        "url": url,
    }


def encode_cursor(cursor: FeedbackListCursor) -> str:
    """Encode a feedback list cursor as opaque base64url JSON."""

    payload = {
        "id": str(cursor.id),
        "ingested_at": serialize_datetime(cursor.ingested_at),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(value: str | None) -> FeedbackListCursor | None:
    """Decode a feedback list cursor from opaque base64url JSON."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise FeedbackQueryValidationError("cursor must not be blank when provided")

    padded = normalized + ("=" * (-len(normalized) % 4))

    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise FeedbackQueryValidationError(
            "cursor must be a valid list_feedback cursor"
        ) from exc

    if not isinstance(payload, dict):
        raise FeedbackQueryValidationError("cursor must be a valid list_feedback cursor")

    ingested_at_raw = payload.get("ingested_at")
    id_raw = payload.get("id")

    if not isinstance(ingested_at_raw, str) or not isinstance(id_raw, str):
        raise FeedbackQueryValidationError("cursor must be a valid list_feedback cursor")

    try:
        cursor_id = UUID(id_raw)
    except ValueError as exc:
        raise FeedbackQueryValidationError(
            "cursor must be a valid list_feedback cursor"
        ) from exc

    return FeedbackListCursor(
        ingested_at=parse_timestamp(ingested_at_raw, field_name="cursor.ingested_at"),
        id=cursor_id,
    )
