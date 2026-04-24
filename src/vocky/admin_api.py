"""Admin REST API routes."""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.feedback import (
    FeedbackEventRecord,
    FeedbackPersistenceError,
    FeedbackQueryFilters,
    FeedbackReadError,
    ListFeedbackQuery,
    get_feedback_service,
)
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    decode_cursor,
    encode_cursor,
    normalize_feedback_value,
    normalize_limit,
    normalize_optional_text,
    normalize_tag,
    parse_timestamp,
    serialize_datetime,
    validate_time_window,
)


class AdminFeedbackPatchInput(BaseModel):
    """Raw Admin REST patch body."""

    feedback_value: int | None = None
    comment: str | None = None
    channel: str | None = None
    tags: list[str] | None = None
    source_metadata: dict[str, object] | None = None
    attributes: dict[str, object] | None = None


async def admin_healthz(_: Request) -> JSONResponse:
    """Return a simple Admin API liveness response."""

    return JSONResponse({"service": "vocky", "surface": "admin", "status": "ok"})


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


def parse_feedback_id(request: Request) -> UUID:
    """Parse the feedback ID path parameter."""

    try:
        return UUID(request.path_params["feedback_id"])
    except ValueError as exc:
        raise FeedbackQueryValidationError("feedback_id must be a valid UUID") from exc


def normalize_tags(tags: list[str] | None) -> list[str] | None:
    """Trim optional tags and reject blanks or duplicates."""

    if tags is None:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned:
            raise FeedbackQueryValidationError("tags must not contain blank values")
        if cleaned in seen:
            raise FeedbackQueryValidationError("tags must not contain duplicates")
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def serialize_record(record: FeedbackEventRecord) -> dict[str, object]:
    """Serialize a feedback record for Admin REST responses."""

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


def normalize_list_query(request: Request) -> ListFeedbackQuery:
    """Normalize Admin feedback list query parameters."""

    params = request.query_params
    start_ingested_at = parse_timestamp(
        params.get("start_ingested_at"),
        field_name="start_ingested_at",
    )
    end_ingested_at = parse_timestamp(
        params.get("end_ingested_at"),
        field_name="end_ingested_at",
    )
    validate_time_window(start_ingested_at, end_ingested_at)

    return ListFeedbackQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start_ingested_at,
            end_ingested_at=end_ingested_at,
            source_product=normalize_optional_text(params.get("source_product")),
            source_integration=normalize_optional_text(params.get("source_integration")),
            conversation_id=normalize_optional_text(params.get("conversation_id")),
            session_id=normalize_optional_text(params.get("session_id")),
            feedback_value=normalize_feedback_value(
                parse_int_param(params.get("feedback_value"), field_name="feedback_value")
            ),
            channel=normalize_optional_text(params.get("channel")),
            tag=normalize_tag(params.get("tag")),
        ),
        limit=normalize_limit(parse_int_param(params.get("limit"), field_name="limit")),
        cursor=decode_cursor(params.get("cursor")),
    )


async def list_admin_feedback(request: Request) -> JSONResponse:
    """List all feedback records for human/operator review."""

    try:
        query = normalize_list_query(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        page = await get_feedback_service().list_feedback(query)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload: dict[str, object] = {
        "records": [serialize_record(record) for record in page.records],
    }
    if page.next_cursor is not None:
        payload["next_cursor"] = encode_cursor(page.next_cursor)

    return JSONResponse(payload)


async def get_admin_feedback(request: Request) -> Response:
    """Return one feedback record for human/operator review."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        record = await get_feedback_service().get_feedback_event(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    return JSONResponse({"record": serialize_record(record)})


async def patch_admin_feedback(request: Request) -> Response:
    """Patch review-oriented fields on one feedback record."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        raw_body = await request.json()
        patch = AdminFeedbackPatchInput.model_validate(raw_body)
    except (json.JSONDecodeError, ValidationError):
        return JSONResponse({"detail": "request body must be a valid JSON object"}, status_code=400)

    updates: dict[str, object] = {}
    try:
        if "feedback_value" in patch.model_fields_set:
            updates["feedback_value"] = normalize_feedback_value(patch.feedback_value)
        if "comment" in patch.model_fields_set:
            updates["comment"] = normalize_optional_text(patch.comment)
        if "channel" in patch.model_fields_set:
            updates["channel"] = normalize_optional_text(patch.channel)
        if "tags" in patch.model_fields_set:
            updates["tags"] = normalize_tags(patch.tags) or []
        if "source_metadata" in patch.model_fields_set:
            updates["source_metadata"] = patch.source_metadata or {}
        if "attributes" in patch.model_fields_set:
            updates["attributes"] = patch.attributes or {}
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    if not updates:
        return JSONResponse({"detail": "request body must include at least one editable field"}, status_code=400)

    try:
        record = await get_feedback_service().update_feedback_event(feedback_id, updates)
    except FeedbackPersistenceError:
        return JSONResponse({"detail": "storage write failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    return JSONResponse({"record": serialize_record(record)})


async def delete_admin_feedback(request: Request) -> Response:
    """Delete one feedback record."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        deleted = await get_feedback_service().delete_feedback_event(feedback_id)
    except FeedbackPersistenceError:
        return JSONResponse({"detail": "storage write failed"}, status_code=500)

    if not deleted:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    return Response(status_code=204)


routes = [
    Route("/admin/api/healthz", admin_healthz, methods=["GET"]),
    Route("/admin/api/feedback", list_admin_feedback, methods=["GET"]),
    Route("/admin/api/feedback/{feedback_id}", get_admin_feedback, methods=["GET"]),
    Route("/admin/api/feedback/{feedback_id}", patch_admin_feedback, methods=["PATCH"]),
    Route("/admin/api/feedback/{feedback_id}", delete_admin_feedback, methods=["DELETE"]),
]
