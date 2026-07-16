"""Admin REST API routes."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.channel import ChannelValidationError, normalize_channel_write
from vocky.feedback import (
    CreateFeedbackComment,
    FeedbackDailyMetricCount,
    FeedbackMetricCounts,
    FeedbackMetrics,
    FeedbackMetricsQuery,
    FeedbackPersistenceError,
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
    serialize_record,
    validate_time_window,
)

logger = logging.getLogger(__name__)


class AdminFeedbackPatchInput(BaseModel):
    """Raw Admin REST patch body."""

    feedback_value: int | None = None
    comment: str | None = None
    channel: str | None = None
    tags: list[str] | None = None
    source_metadata: dict[str, object] | None = None
    attributes: dict[str, object] | None = None


class AdminFeedbackCommentInput(BaseModel):
    """Raw Admin REST operator-comment body."""

    author: str | None = None
    body: str


async def admin_healthz(_: Request) -> JSONResponse:
    """Return a simple Admin API liveness response."""

    return JSONResponse({"service": "vocky", "surface": "admin", "status": "ok"})


def parse_feedback_id(request: Request) -> UUID:
    """Parse the feedback ID path parameter."""

    try:
        return UUID(request.path_params["feedback_id"])
    except ValueError as exc:
        raise FeedbackQueryValidationError("feedback_id must be a valid UUID") from exc


def parse_attachment_id(request: Request) -> UUID:
    """Parse the attachment ID path parameter."""

    try:
        return UUID(request.path_params["attachment_id"])
    except ValueError as exc:
        raise FeedbackQueryValidationError("attachment_id must be a valid UUID") from exc


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


def normalize_admin_channel_write(value: str | None) -> str | None:
    """Normalize and validate a channel write from Admin REST."""

    try:
        return normalize_channel_write(value)
    except ChannelValidationError as exc:
        raise FeedbackQueryValidationError(str(exc)) from exc


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
            user_id=normalize_optional_text(params.get("user_id")),
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


def parse_required_timestamp(request: Request, *, field_name: str) -> datetime:
    """Parse a required timestamp query parameter."""

    parsed = parse_timestamp(
        request.query_params.get(field_name),
        field_name=field_name,
    )
    if parsed is None:
        raise FeedbackQueryValidationError(f"{field_name} is required")
    return parsed


def normalize_metrics_query(request: Request) -> FeedbackMetricsQuery:
    """Normalize Admin feedback metrics query parameters."""

    start_ingested_at = parse_required_timestamp(
        request,
        field_name="start_ingested_at",
    )
    end_ingested_at = parse_required_timestamp(
        request,
        field_name="end_ingested_at",
    )
    validate_time_window(start_ingested_at, end_ingested_at)

    return FeedbackMetricsQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start_ingested_at,
            end_ingested_at=end_ingested_at,
        )
    )


def serialize_metric_counts(counts: FeedbackMetricCounts) -> dict[str, int]:
    """Serialize aggregate metric counts."""

    return {
        "total": counts.total,
        "liked": counts.liked,
        "disliked": counts.disliked,
        "unrated": counts.unrated,
    }


def serialize_daily_metric_count(
    daily_count: FeedbackDailyMetricCount,
) -> dict[str, object]:
    """Serialize one daily metric bucket."""

    return {
        "day": daily_count.day.isoformat(),
        "total": daily_count.total,
        "liked": daily_count.liked,
        "disliked": daily_count.disliked,
        "unrated": daily_count.unrated,
    }


def serialize_metrics(
    metrics: FeedbackMetrics,
    query: FeedbackMetricsQuery,
) -> dict[str, object]:
    """Serialize dashboard feedback metrics."""

    start_ingested_at = query.filters.start_ingested_at
    end_ingested_at = query.filters.end_ingested_at
    assert start_ingested_at is not None
    assert end_ingested_at is not None

    return {
        "window": {
            "start_ingested_at": serialize_datetime(start_ingested_at),
            "end_ingested_at": serialize_datetime(end_ingested_at),
        },
        "totals": serialize_metric_counts(metrics.totals),
        "daily_counts": [
            serialize_daily_metric_count(daily_count)
            for daily_count in metrics.daily_counts
        ],
    }


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


async def get_admin_feedback_metrics(request: Request) -> JSONResponse:
    """Return dashboard metrics for human/operator review."""

    try:
        query = normalize_metrics_query(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        metrics = await get_feedback_service().get_feedback_metrics(query)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    return JSONResponse(serialize_metrics(metrics, query))


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

    try:
        comments = await get_feedback_service().list_feedback_comments(feedback_id)
        attachments = await get_feedback_service().list_feedback_attachments(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload = serialize_record(record)
    payload["comments"] = [serialize_comment(comment) for comment in comments]
    payload["attachments"] = [
        serialize_attachment(
            attachment,
            url=f"/admin/api/feedback/{feedback_id}/attachments/{attachment.id}",
        )
        for attachment in attachments
    ]
    return JSONResponse({"record": payload})


async def post_admin_feedback_comment(request: Request) -> Response:
    """Add one operator-authored comment to a feedback record."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        raw_body = await request.json()
        payload = AdminFeedbackCommentInput.model_validate(raw_body)
    except (json.JSONDecodeError, ValidationError):
        return JSONResponse(
            {"detail": "request body must be a valid JSON object"}, status_code=400
        )

    body = payload.body.strip()
    if not body:
        return JSONResponse({"detail": "body must not be blank"}, status_code=400)
    author = normalize_optional_text(payload.author)

    try:
        record = await get_feedback_service().get_feedback_event(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    try:
        comment = await get_feedback_service().create_feedback_comment(
            CreateFeedbackComment(feedback_id=feedback_id, body=body, author=author)
        )
    except FeedbackPersistenceError:
        return JSONResponse({"detail": "storage write failed"}, status_code=500)

    return JSONResponse({"comment": serialize_comment(comment)}, status_code=201)


async def list_admin_feedback_comments(request: Request) -> Response:
    """List one feedback record's operator comments, oldest-first."""

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

    try:
        comments = await get_feedback_service().list_feedback_comments(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    return JSONResponse(
        {"comments": [serialize_comment(comment) for comment in comments]}
    )


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
            updates["channel"] = normalize_admin_channel_write(patch.channel)
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


async def download_admin_feedback_attachment(request: Request) -> Response:
    """Stream one feedback attachment for operator review.

    Operators see all attachments for any feedback (admin token only); the
    attachment must be linked to the feedback in the path, else 404.
    """

    try:
        feedback_id = parse_feedback_id(request)
        attachment_id = parse_attachment_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        attachment = await get_feedback_service().get_admin_attachment(
            feedback_id=feedback_id,
            attachment_id=attachment_id,
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
        headers={"X-Content-Type-Options": "nosniff"},
    )


async def delete_admin_feedback(request: Request) -> Response:
    """Delete one feedback record and best-effort delete its attachment files."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        deleted, storage_keys = await get_feedback_service().delete_feedback_event(
            feedback_id
        )
    except FeedbackPersistenceError:
        return JSONResponse({"detail": "storage write failed"}, status_code=500)

    if not deleted:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    # The DB rows are gone (source of truth); clean up the files best-effort.
    storage = get_attachment_storage()
    for storage_key in storage_keys:
        try:
            storage.delete(storage_key)
        except StorageError:
            logger.warning(
                "failed to delete attachment object %s for feedback %s",
                storage_key,
                feedback_id,
            )

    return Response(status_code=204)


routes = [
    Route("/admin/api/healthz", admin_healthz, methods=["GET"]),
    Route("/admin/api/feedback", list_admin_feedback, methods=["GET"]),
    Route("/admin/api/feedback/metrics", get_admin_feedback_metrics, methods=["GET"]),
    Route(
        "/admin/api/feedback/{feedback_id}/comments",
        list_admin_feedback_comments,
        methods=["GET"],
    ),
    Route(
        "/admin/api/feedback/{feedback_id}/comments",
        post_admin_feedback_comment,
        methods=["POST"],
    ),
    Route(
        "/admin/api/feedback/{feedback_id}/attachments/{attachment_id}",
        download_admin_feedback_attachment,
        methods=["GET"],
    ),
    Route("/admin/api/feedback/{feedback_id}", get_admin_feedback, methods=["GET"]),
    Route("/admin/api/feedback/{feedback_id}", patch_admin_feedback, methods=["PATCH"]),
    Route("/admin/api/feedback/{feedback_id}", delete_admin_feedback, methods=["DELETE"]),
]
