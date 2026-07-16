"""Public REST API routes."""

from __future__ import annotations

import json
import logging
from urllib.parse import quote
from uuid import UUID

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.capture import (
    CaptureFeedbackValidationError,
    RestCaptureFeedbackInput,
    normalize_rest_payload,
    serialize_capture_receipt,
)
from vocky.auth import get_request_credential
from vocky.capture_queue import CaptureQueueError, get_capture_queue
from vocky.feedback import (
    FeedbackAttachmentRecord,
    FeedbackCommentRecord,
    FeedbackEventRecord,
    FeedbackQueryFilters,
    FeedbackReadError,
    ListFeedbackQuery,
    get_feedback_service,
)
from vocky.storage import (
    StorageError,
    StorageObjectNotFoundError,
    get_attachment_storage,
)
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    decode_cursor,
    encode_cursor,
    normalize_feedback_value,
    normalize_limit,
    normalize_optional_text,
    normalize_tag,
    normalize_target_type_filter,
    normalize_trigger_type_filter,
    parse_int_param,
    parse_timestamp,
    serialize_attachment,
    serialize_comment,
    serialize_datetime,
    validate_time_window,
)

logger = logging.getLogger(__name__)


class CaptureAPIValidationError(ValueError):
    """Raised when a REST capture request body is invalid."""


def format_pydantic_error(exc: ValidationError) -> str:
    """Format the first Pydantic validation error for REST clients."""

    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = str(first_error.get("msg", "invalid value"))
    if location:
        return f"{location}: {message}"
    return message


async def parse_capture_request(request: Request) -> RestCaptureFeedbackInput:
    """Parse and validate the JSON request body shape."""

    try:
        raw_body = await request.json()
    except json.JSONDecodeError as exc:
        raise CaptureAPIValidationError("request body must be valid JSON") from exc

    if not isinstance(raw_body, dict):
        raise CaptureAPIValidationError("request body must be a JSON object")

    try:
        return RestCaptureFeedbackInput.model_validate(raw_body)
    except ValidationError as exc:
        raise CaptureAPIValidationError(format_pydantic_error(exc)) from exc


async def capture_feedback(request: Request) -> JSONResponse:
    """Capture a single feedback event through REST."""

    try:
        raw_payload = await parse_capture_request(request)
        normalized = normalize_rest_payload(raw_payload)
    except (CaptureAPIValidationError, CaptureFeedbackValidationError) as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    normalized.payload.project_id = get_request_credential(request).project_id

    try:
        receipt = await get_capture_queue().enqueue_feedback(normalized.payload)
    except CaptureQueueError:
        logger.exception("Failed to enqueue captured feedback event")
        return JSONResponse({"detail": "capture queue unavailable"}, status_code=503)

    response = serialize_capture_receipt(
        request_id=receipt.request_id,
        accepted_at=receipt.accepted_at,
    )
    return JSONResponse(response.model_dump(mode="json"), status_code=202)


def require_scope_value(value: str | None, *, field_name: str) -> str:
    """Return a required, non-blank scope query parameter or raise.

    `user_id` and `source_product` form the read's scoping boundary: the read is
    never issued unscoped, so these are required and must be non-blank.
    """

    if value is None:
        raise FeedbackQueryValidationError(f"{field_name} is required")
    trimmed = value.strip()
    if not trimmed:
        raise FeedbackQueryValidationError(f"{field_name} must not be blank")
    return trimmed


def normalize_user_feedback_query(request: Request) -> ListFeedbackQuery:
    """Normalize the scoped end-user feedback read query parameters.

    Requires non-blank `user_id` and `source_product`; all other supported filters
    are optional and AND-combined with the required scope, so the caller can only
    ever read their own records under their own product.
    """

    params = request.query_params
    user_id = require_scope_value(params.get("user_id"), field_name="user_id")
    source_product = require_scope_value(
        params.get("source_product"), field_name="source_product"
    )

    start_ingested_at = parse_timestamp(
        params.get("start_ingested_at"), field_name="start_ingested_at"
    )
    end_ingested_at = parse_timestamp(
        params.get("end_ingested_at"), field_name="end_ingested_at"
    )
    validate_time_window(start_ingested_at, end_ingested_at)

    return ListFeedbackQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start_ingested_at,
            end_ingested_at=end_ingested_at,
            source_product=source_product,
            source_integration=normalize_optional_text(params.get("source_integration")),
            conversation_id=normalize_optional_text(params.get("conversation_id")),
            session_id=normalize_optional_text(params.get("session_id")),
            user_id=user_id,
            trigger_type=normalize_trigger_type_filter(params.get("trigger_type")),
            feedback_value=normalize_feedback_value(
                parse_int_param(params.get("feedback_value"), field_name="feedback_value")
            ),
            channel=normalize_optional_text(params.get("channel")),
            target_type=normalize_target_type_filter(params.get("target_type")),
            tag=normalize_tag(params.get("tag")),
        ),
        limit=normalize_limit(parse_int_param(params.get("limit"), field_name="limit")),
        cursor=decode_cursor(params.get("cursor")),
    )


def serialize_user_feedback_record(
    record: FeedbackEventRecord,
    comments: tuple[FeedbackCommentRecord, ...],
    attachments: tuple[FeedbackAttachmentRecord, ...],
) -> dict[str, object]:
    """Serialize a feedback record plus operator comments and attachments."""

    return {
        "id": str(record.id),
        "message": record.message,
        "source_product": record.source_product,
        "feedback_value": record.feedback_value,
        "comment": record.comment,
        "channel": record.channel,
        "source_integration": record.source_integration,
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
        "comments": [serialize_comment(comment) for comment in comments],
        "attachments": [
            serialize_attachment(
                attachment,
                url=f"/api/feedback/{record.id}/attachments/{attachment.id}",
            )
            for attachment in attachments
        ],
    }


async def list_user_feedback(request: Request) -> JSONResponse:
    """Return one end user's own feedback plus operator comments.

    Scoped strictly by required `user_id` + `source_product` and, defense in
    depth, by the authenticating credential's project; never returns cross-user,
    cross-product, or cross-project data. Legacy rows with a NULL `project_id`
    fall out of the scoped read (acceptable pre-MVP).
    """

    try:
        query = normalize_user_feedback_query(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # Defense in depth (D-P3-6): the self-read is additionally scoped to the
    # authenticating credential's project, on top of user_id + source_product.
    query.filters.project_id = get_request_credential(request).project_id

    try:
        (
            page,
            comments_by_id,
            attachments_by_id,
        ) = await get_feedback_service().list_feedback_with_comments_and_attachments(
            query
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload: dict[str, object] = {
        "records": [
            serialize_user_feedback_record(
                record,
                comments_by_id.get(record.id, ()),
                attachments_by_id.get(record.id, ()),
            )
            for record in page.records
        ],
    }
    if page.next_cursor is not None:
        payload["next_cursor"] = encode_cursor(page.next_cursor)

    return JSONResponse(payload)


def parse_uuid_path_param(request: Request, name: str) -> UUID:
    """Parse a UUID path parameter or raise a validation error."""

    try:
        return UUID(request.path_params[name])
    except ValueError as exc:
        raise FeedbackQueryValidationError(f"{name} must be a valid UUID") from exc


def attachment_content_disposition(filename: str | None) -> str:
    """Build a safe `Content-Disposition: attachment` header value."""

    if not filename:
        return "attachment"
    ascii_fallback = (
        filename.encode("ascii", "ignore").decode("ascii").replace('"', "").strip()
        or "download"
    )
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


async def download_user_feedback_attachment(request: Request) -> Response:
    """Stream one of the caller's own feedback attachments.

    Scoped strictly by required `user_id` + `source_product` and authorized off
    the linked feedback row; any mismatch, unlinked attachment, or missing row
    answers 404 so existence is never leaked across users or products.
    """

    try:
        feedback_id = parse_uuid_path_param(request, "feedback_id")
        attachment_id = parse_uuid_path_param(request, "attachment_id")
        user_id = require_scope_value(
            request.query_params.get("user_id"), field_name="user_id"
        )
        source_product = require_scope_value(
            request.query_params.get("source_product"), field_name="source_product"
        )
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        attachment = await get_feedback_service().get_user_attachment(
            feedback_id=feedback_id,
            attachment_id=attachment_id,
            user_id=user_id,
            source_product=source_product,
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if attachment is None:
        return JSONResponse({"detail": "attachment not found"}, status_code=404)

    storage = get_attachment_storage()
    try:
        data = storage.load(attachment.storage_key)
    except StorageObjectNotFoundError:
        logger.warning("attachment %s has no stored object", attachment.id)
        return JSONResponse({"detail": "attachment not found"}, status_code=404)
    except StorageError:
        logger.exception("failed to read attachment object")
        return JSONResponse(
            {"detail": "attachment storage unavailable"}, status_code=503
        )

    return Response(
        content=data,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": attachment_content_disposition(attachment.filename),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


routes = [
    Route("/api/feedback", capture_feedback, methods=["POST"]),
    Route("/api/feedback", list_user_feedback, methods=["GET"]),
    Route(
        "/api/feedback/{feedback_id}/attachments/{attachment_id}",
        download_user_feedback_attachment,
        methods=["GET"],
    ),
]
