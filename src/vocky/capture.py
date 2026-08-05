"""Transport-neutral feedback capture validation and response models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from vocky.accounts import DEFAULT_PROJECT_NAME, get_accounts_service
from vocky.accounts.types import ProjectCredentialRecord
from vocky.channel import ChannelValidationError, normalize_channel_write
from vocky.config import get_settings
from vocky.feedback import CreateFeedbackEvent
from vocky.recorded_by import RecordedByValidationError, normalize_recorded_by
from vocky.trigger import TriggerTypeValidationError, normalize_trigger_type

ALLOWED_TARGET_TYPES = frozenset({"message", "conversation", "surface"})
ALLOWED_TARGET_ROLES = frozenset({"user", "assistant", "system", "tool"})


class CaptureFeedbackValidationError(ValueError):
    """Raised when capture input is semantically invalid."""


class CaptureFeedbackSourceInput(BaseModel):
    """Raw nested source input."""

    product: str
    integration: str | None = None


class BaseCaptureFeedbackInput(BaseModel):
    """Shared raw capture fields before transport-specific normalization."""

    message: str
    source: CaptureFeedbackSourceInput
    feedback_value: int | None = None
    comment: str | None = None
    channel: str | None = None
    recorded_by: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    trigger_type: str | None = None
    trigger_message: str | None = None
    trigger_metadata: Any = Field(default_factory=dict)
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


class McpCaptureFeedbackInput(BaseCaptureFeedbackInput):
    """Raw feedback capture input received through MCP.

    Agents have no upload flow, so MCP capture stays attachment-free; the
    ``attachment_ids`` field is declared only on the REST subclass.
    """


class RestCaptureFeedbackInput(BaseCaptureFeedbackInput):
    """Raw feedback capture input received through public REST.

    REST capture may reference previously uploaded attachments by id.

    ``project`` names the destination project for an **org-level** ``vk_`` key
    (get-or-created under the key's org, defaulting to ``"default"``). A
    project-bound key ignores it entirely — see :func:`resolve_capture_project`.
    Purely additive: pydantic defaults to ``extra="ignore"``, so clients that
    never send it are unaffected.
    """

    attachment_ids: list[str] | None = None
    project: str | None = None


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


def normalize_capture_channel(value: str | None) -> str | None:
    """Normalize and validate a channel write from a capture transport."""

    try:
        return normalize_channel_write(value)
    except ChannelValidationError as exc:
        raise CaptureFeedbackValidationError(str(exc)) from exc


def normalize_capture_trigger_type(value: str | None) -> str | None:
    """Normalize and validate a trigger type from a capture transport."""

    try:
        return normalize_trigger_type(value)
    except TriggerTypeValidationError as exc:
        raise CaptureFeedbackValidationError(str(exc)) from exc


def normalize_capture_recorded_by(value: str | None) -> str | None:
    """Normalize and validate a recorded_by marker from a capture transport."""

    try:
        return normalize_recorded_by(value)
    except RecordedByValidationError as exc:
        raise CaptureFeedbackValidationError(str(exc)) from exc


def normalize_json_array(value: list[Any] | None, *, field_name: str) -> tuple[Any, ...]:
    """Normalize an optional JSON array field."""

    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaptureFeedbackValidationError(f"{field_name} must be a JSON array")
    return tuple(value)


def normalize_json_object(value: Any, *, field_name: str) -> dict[str, Any]:
    """Normalize an optional JSON object field."""

    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CaptureFeedbackValidationError(f"{field_name} must be a JSON object")
    return dict(value)


def normalize_attachment_ids(values: list[str] | None) -> tuple[UUID, ...]:
    """Parse, dedupe, and bound a list of referenced attachment ids.

    Each value must be a valid UUID; duplicates are dropped; the count must not
    exceed the configured per-feedback maximum. The link is additionally
    re-guarded by scope at persist time.
    """

    if not values:
        return ()

    seen: set[UUID] = set()
    normalized: list[UUID] = []
    for raw_value in values:
        try:
            parsed = UUID(str(raw_value).strip())
        except ValueError as exc:
            raise CaptureFeedbackValidationError(
                "attachment_ids must be valid UUIDs"
            ) from exc
        if parsed in seen:
            continue
        seen.add(parsed)
        normalized.append(parsed)

    max_count = get_settings().attachments_max_count
    if len(normalized) > max_count:
        raise CaptureFeedbackValidationError(
            f"attachment_ids must not exceed {max_count} items"
        )

    return tuple(normalized)


def _normalize_capture_payload(raw: BaseCaptureFeedbackInput) -> NormalizedCaptureFeedback:
    """Normalize and validate a raw capture payload into the shared service type."""

    normalized_event_at = parse_event_at(raw.event_at)
    payload = CreateFeedbackEvent(
        message=require_non_blank(raw.message, "message"),
        source_product=require_non_blank(raw.source.product, "source.product"),
        feedback_value=normalize_feedback_value(raw.feedback_value),
        comment=normalize_optional_text(raw.comment),
        channel=normalize_capture_channel(raw.channel),
        source_integration=normalize_optional_text(raw.source.integration),
        recorded_by=normalize_capture_recorded_by(raw.recorded_by),
        conversation_id=normalize_optional_text(raw.conversation_id),
        session_id=normalize_optional_text(raw.session_id),
        user_id=normalize_optional_text(raw.user_id),
        trigger_type=normalize_capture_trigger_type(raw.trigger_type),
        trigger_message=normalize_optional_text(raw.trigger_message),
        trigger_metadata=normalize_json_object(
            raw.trigger_metadata,
            field_name="trigger_metadata",
        ),
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
        attachment_ids=normalize_attachment_ids(getattr(raw, "attachment_ids", None)),
    )
    return NormalizedCaptureFeedback(
        payload=payload,
        normalized_event_at=normalized_event_at,
    )


#: What ``recorded_by`` means on an MCP capture that never states it. ``/mcp`` is
#: by construction the agent-runtime surface — one write-only tool, no
#: human-driven client — so the default *corrects* the record rather than
#: guessing. REST is genuinely mixed and stays ``None`` (unspecified).
MCP_DEFAULT_RECORDED_BY = "agent"


def normalize_mcp_payload(raw: McpCaptureFeedbackInput) -> NormalizedCaptureFeedback:
    """Normalize and validate a raw MCP capture payload.

    Transport-specific behavior lives here, not in
    :func:`_normalize_capture_payload`: an MCP caller that omits (or blanks)
    ``recorded_by`` is stamped ``"agent"``; an explicit value always wins.
    """

    normalized = _normalize_capture_payload(raw)
    if normalized.payload.recorded_by is None:
        normalized.payload.recorded_by = MCP_DEFAULT_RECORDED_BY
    return normalized


def normalize_rest_payload(raw: RestCaptureFeedbackInput) -> NormalizedCaptureFeedback:
    """Normalize and validate a raw REST capture payload."""

    return _normalize_capture_payload(raw)


#: Upper bound on a capture-supplied project name, mirroring the ``/app/projects``
#: create body (``vocky.app_api.CreateProjectInput``). ``projects.name`` is an
#: unbounded ``Text`` column, and this value becomes a get-or-create key.
MAX_CAPTURE_PROJECT_NAME_LENGTH = 200


async def resolve_capture_project(
    credential: ProjectCredentialRecord,
    project_name: str | None,
) -> UUID:
    """Resolve the project a capture lands in, for either credential shape.

    The **single** ingest-side project resolver, shared by REST
    (:func:`vocky.api.capture_feedback`) and MCP
    (:func:`vocky.tools.capture_feedback.capture_feedback`):

    - a **project-bound** credential lands in its bound project and
      ``project_name`` is **ignored entirely** — not compared, not rejected. That
      is what keeps every existing client byte-for-byte unchanged;
    - an **org-level** credential (``project_id IS NULL``) lands in the named
      project under its org, get-or-created, defaulting to
      ``DEFAULT_PROJECT_NAME`` when no name is given.

    Never returns ``None``, so an org-level key can never enqueue an orphan row:
    ``vocky.capture_queue`` round-trips ``project_id`` nullably and the worker
    never re-derives it, which makes enqueue the **last** enforcement point.

    Raises :class:`CaptureFeedbackValidationError` on an over-long name;
    ``AccountsPersistenceError`` / ``AccountsReadError`` propagate.
    """

    if credential.project_id is not None:
        return credential.project_id

    name = normalize_optional_text(project_name) or DEFAULT_PROJECT_NAME
    if len(name) > MAX_CAPTURE_PROJECT_NAME_LENGTH:
        raise CaptureFeedbackValidationError(
            f"project must not exceed {MAX_CAPTURE_PROJECT_NAME_LENGTH} characters"
        )

    project = await get_accounts_service().get_or_create_project(
        credential.tenant_id, name
    )
    return project.id


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
