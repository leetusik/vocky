"""Transport-neutral feedback capture validation and response models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from vocky.feedback import CreateFeedbackEvent

ALLOWED_TARGET_TYPES = frozenset({"message", "conversation", "surface"})
ALLOWED_TARGET_ROLES = frozenset({"user", "assistant", "system", "tool"})


class CaptureFeedbackValidationError(ValueError):
    """Raised when capture input is semantically invalid."""


class CaptureFeedbackSourceInput(BaseModel):
    """Raw nested source input."""

    product: str
    integration: str | None = None


class CaptureFeedbackInput(BaseModel):
    """Raw feedback capture input."""

    message: str
    source: CaptureFeedbackSourceInput
    feedback_value: int | None = None
    comment: str | None = None
    channel: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    target_role: str | None = None
    target_text: str | None = None
    event_at: str | None = None
    tags: list[str] | None = None
    messages: list[Any] | None = None
    used_context: list[Any] | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class CaptureFeedbackResponse(BaseModel):
    """Structured capture success response."""

    request_id: str
    accepted_at: str
    status: str = "accepted"


@dataclass(slots=True, kw_only=True)
class NormalizedCaptureFeedback:
    """Normalized capture payload ready for the service layer."""

    payload: CreateFeedbackEvent
    normalized_event_at: datetime | None


def normalize_optional_text(value: str | None) -> str | None:
    """Trim optional text fields and collapse blank values to null."""

    if value is None:
        return None

    trimmed = value.strip()
    return trimmed or None


def require_non_blank(value: str, field_name: str) -> str:
    """Trim a required text field and reject blank values."""

    trimmed = value.strip()
    if not trimmed:
        raise CaptureFeedbackValidationError(f"{field_name} must not be blank")
    return trimmed


def parse_event_at(value: str | None) -> datetime | None:
    """Parse an optional ISO 8601 timestamp and normalize it to UTC."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise CaptureFeedbackValidationError("event_at must not be blank when provided")

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureFeedbackValidationError("event_at must be a valid ISO 8601 timestamp") from exc

    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise CaptureFeedbackValidationError("event_at must include a timezone offset")

    return parsed.astimezone(UTC)


def normalize_tags(tags: list[str] | None) -> tuple[str, ...]:
    """Trim tags, reject blanks, and reject duplicates after normalization."""

    if tags is None:
        return ()

    normalized: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        cleaned = tag.strip()
        if not cleaned:
            raise CaptureFeedbackValidationError("tags must not contain blank values")
        if cleaned in seen:
            raise CaptureFeedbackValidationError("tags must not contain duplicates")
        seen.add(cleaned)
        normalized.append(cleaned)

    return tuple(normalized)


def normalize_feedback_value(value: int | None) -> int | None:
    """Validate an optional explicit action feedback value."""

    if value is None:
        return None
    if isinstance(value, bool) or value not in (1, 2):
        raise CaptureFeedbackValidationError("feedback_value must be 1 for like or 2 for dislike")
    return value


def normalize_target_type(value: str | None) -> str | None:
    """Normalize and validate an optional feedback target type."""

    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    if normalized not in ALLOWED_TARGET_TYPES:
        raise CaptureFeedbackValidationError(
            "target_type must be one of: message, conversation, surface"
        )
    return normalized


def normalize_target_role(value: str | None) -> str | None:
    """Normalize and validate an optional feedback target role."""

    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    if normalized not in ALLOWED_TARGET_ROLES:
        raise CaptureFeedbackValidationError(
            "target_role must be one of: user, assistant, system, tool"
        )
    return normalized


def normalize_json_array(value: list[Any] | None, *, field_name: str) -> tuple[Any, ...]:
    """Normalize an optional JSON array field."""

    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaptureFeedbackValidationError(f"{field_name} must be a JSON array")
    return tuple(value)


def normalize_payload(raw: CaptureFeedbackInput) -> NormalizedCaptureFeedback:
    """Normalize and validate a raw capture payload."""

    normalized_event_at = parse_event_at(raw.event_at)
    payload = CreateFeedbackEvent(
        message=require_non_blank(raw.message, "message"),
        source_product=require_non_blank(raw.source.product, "source.product"),
        feedback_value=normalize_feedback_value(raw.feedback_value),
        comment=normalize_optional_text(raw.comment),
        channel=normalize_optional_text(raw.channel),
        source_integration=normalize_optional_text(raw.source.integration),
        conversation_id=normalize_optional_text(raw.conversation_id),
        session_id=normalize_optional_text(raw.session_id),
        target_type=normalize_target_type(raw.target_type),
        target_id=normalize_optional_text(raw.target_id),
        target_role=normalize_target_role(raw.target_role),
        target_text=normalize_optional_text(raw.target_text),
        event_at=normalized_event_at,
        tags=normalize_tags(raw.tags),
        messages=normalize_json_array(raw.messages, field_name="messages"),
        used_context=normalize_json_array(raw.used_context, field_name="used_context"),
        source_metadata=dict(raw.source_metadata),
        attributes=dict(raw.attributes),
    )
    return NormalizedCaptureFeedback(
        payload=payload,
        normalized_event_at=normalized_event_at,
    )


def serialize_datetime(value: datetime) -> str:
    """Serialize a timestamp as UTC ISO 8601."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def serialize_capture_receipt(
    *,
    request_id: UUID,
    accepted_at: datetime,
) -> CaptureFeedbackResponse:
    """Create the public accepted-capture response from a queue receipt."""

    return CaptureFeedbackResponse(
        request_id=str(request_id),
        accepted_at=serialize_datetime(accepted_at),
    )
