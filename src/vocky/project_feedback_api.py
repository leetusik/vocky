"""Project-scoped feedback review + manage REST routes (``/api/project/*``).

These routes let an ingest ``vk_`` credential read and manage the feedback
**inside its own scope**: list / get-one (+comments+attachments) / patch review
fields / delete / operator comments (add + list) / attachment download. They
port the operator verbs from :mod:`vocky.admin_api`; the only new logic is
project scoping.

The authenticating scope comes from the credential the
``ProjectCredentialAuthMiddleware`` resolved onto the ASGI scope (via
:func:`vocky.auth.get_request_project_ids`) — never a path or query parameter.
It is one project for today's project-bound key and the org's whole project set
for an org-level key (P10); it is a ``tuple``, never ``None``, because a ``None``
project filter reads every project in every tenant. Every per-feedback op loads
through :func:`_load_project_feedback`, which answers **404 (never 403)** on any
feedback id outside that scope, so cross-project existence is never leaked
(mirrors the D-P2-5 cross-tenant isolation stance).
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.admin_api import (
    AdminFeedbackCommentInput,
    AdminFeedbackPatchInput,
    normalize_admin_channel_write,
    normalize_list_query,
    normalize_tags,
    parse_attachment_id,
    parse_feedback_id,
)
from vocky.accounts import ProjectCredentialRecord
from vocky.auth import get_request_credential, get_request_project_ids
from vocky.feedback import (
    CreateFeedbackComment,
    FeedbackEventRecord,
    FeedbackPersistenceError,
    FeedbackReadError,
    get_feedback_service,
)
from vocky.storage import (
    StorageError,
    StorageObjectNotFoundError,
    get_attachment_storage,
)
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    encode_cursor,
    normalize_feedback_value,
    normalize_optional_text,
    serialize_attachment,
    serialize_comment,
    serialize_record,
)

logger = logging.getLogger(__name__)


async def _load_project_feedback(
    feedback_id: UUID,
    project_ids: tuple[UUID, ...],
) -> FeedbackEventRecord | None:
    """Load a feedback record only when its project is in ``project_ids``.

    Returns ``None`` both when the record is missing and when it belongs to a
    project outside the caller's scope — callers turn ``None`` into a 404 so
    cross-project existence never leaks. May raise :class:`FeedbackReadError`;
    callers map that to a 500.

    Set membership rather than equality (mirroring
    :func:`vocky.app_feedback_api._load_scoped_feedback`) also excludes legacy
    NULL-``project_id`` rows for free: ``None not in (...)`` is always true,
    where an equality check would let a NULL-project credential *match* them.
    """

    record = await get_feedback_service().get_feedback_event(feedback_id)
    if record is None or record.project_id not in project_ids:
        return None
    return record


def _serialize_scoped_record(
    record: FeedbackEventRecord,
    credential: ProjectCredentialRecord,
) -> dict[str, object]:
    """Serialize a feedback record for the credential's scope shape.

    A **project-bound** credential gets the shared serializer verbatim, which
    deliberately omits ``project_id`` because "the project-scoped caller knows
    its own project from its credential" — that premise still holds, and the
    payload stays byte-for-byte identical. An **org-level** credential spans
    many projects, so that premise breaks and the record must say which project
    it belongs to (following :func:`vocky.app_feedback_api._serialize_app_record`).
    """

    payload = serialize_record(record)
    if credential.project_id is None:
        payload["project_id"] = (
            str(record.project_id) if record.project_id is not None else None
        )
    return payload


async def list_project_feedback(request: Request) -> JSONResponse:
    """List the credential's own scope's feedback (filters + keyset paging)."""

    credential = get_request_credential(request)

    try:
        query = normalize_list_query(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # The credential's scope is authoritative and is the *only* source of the
    # project filter (``normalize_admin_list_query`` does not parse
    # ``project_id``, so there is nothing to override and no caller narrowing to
    # preserve — narrowing an org key by ``?project_id`` is a recorded option,
    # not this slice's work).
    scope = get_request_project_ids(request)
    if not scope:
        # An org that owns no projects: an empty page, never an unfiltered
        # ``IN ()`` read (the ``/app/feedback`` empty-scope convention).
        return JSONResponse({"records": []})

    query.filters.project_ids = scope

    try:
        page = await get_feedback_service().list_feedback(query)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload: dict[str, object] = {
        "records": [
            _serialize_scoped_record(record, credential) for record in page.records
        ],
    }
    if page.next_cursor is not None:
        payload["next_cursor"] = encode_cursor(page.next_cursor)

    return JSONResponse(payload)


async def get_project_feedback(request: Request) -> Response:
    """Return one of the scope's feedback records with comments + attachments."""

    credential = get_request_credential(request)

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    try:
        comments = await get_feedback_service().list_feedback_comments(feedback_id)
        attachments = await get_feedback_service().list_feedback_attachments(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload = _serialize_scoped_record(record, credential)
    payload["comments"] = [serialize_comment(comment) for comment in comments]
    payload["attachments"] = [
        serialize_attachment(
            attachment,
            url=f"/api/project/feedback/{feedback_id}/attachments/{attachment.id}",
        )
        for attachment in attachments
    ]
    return JSONResponse({"record": payload})


async def patch_project_feedback(request: Request) -> Response:
    """Patch review-oriented fields on one of the scope's feedback records."""

    credential = get_request_credential(request)

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        raw_body = await request.json()
        patch = AdminFeedbackPatchInput.model_validate(raw_body)
    except (json.JSONDecodeError, ValidationError):
        return JSONResponse(
            {"detail": "request body must be a valid JSON object"}, status_code=400
        )

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
        return JSONResponse(
            {"detail": "request body must include at least one editable field"},
            status_code=400,
        )

    # Verify scope ownership before mutating so an out-of-scope id 404s.
    try:
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    try:
        record = await get_feedback_service().update_feedback_event(feedback_id, updates)
    except FeedbackPersistenceError:
        return JSONResponse({"detail": "storage write failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    return JSONResponse({"record": _serialize_scoped_record(record, credential)})


async def delete_project_feedback(request: Request) -> Response:
    """Delete one of the scope's feedback records (+ best-effort file cleanup)."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

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


async def post_project_feedback_comment(request: Request) -> Response:
    """Add one operator-authored comment to one of the scope's feedback records."""

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
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
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


async def list_project_feedback_comments(request: Request) -> Response:
    """List one of the scope's feedback records' operator comments, oldest-first."""

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
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


async def download_project_feedback_attachment(request: Request) -> Response:
    """Stream one attachment linked to one of the scope's feedback records.

    The parent feedback is scope-verified first (404 on out-of-scope); the
    attachment must be linked to that feedback, else 404.
    """

    try:
        feedback_id = parse_feedback_id(request)
        attachment_id = parse_attachment_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        record = await _load_project_feedback(
            feedback_id, get_request_project_ids(request)
        )
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

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


# Register the ``/comments`` and ``/attachments/{id}`` routes before the bare
# ``/{feedback_id}`` routes so Starlette's first-match resolves them correctly.
routes = [
    Route("/api/project/feedback", list_project_feedback, methods=["GET"]),
    Route(
        "/api/project/feedback/{feedback_id}/comments",
        list_project_feedback_comments,
        methods=["GET"],
    ),
    Route(
        "/api/project/feedback/{feedback_id}/comments",
        post_project_feedback_comment,
        methods=["POST"],
    ),
    Route(
        "/api/project/feedback/{feedback_id}/attachments/{attachment_id}",
        download_project_feedback_attachment,
        methods=["GET"],
    ),
    Route(
        "/api/project/feedback/{feedback_id}",
        get_project_feedback,
        methods=["GET"],
    ),
    Route(
        "/api/project/feedback/{feedback_id}",
        patch_project_feedback,
        methods=["PATCH"],
    ),
    Route(
        "/api/project/feedback/{feedback_id}",
        delete_project_feedback,
        methods=["DELETE"],
    ),
]
