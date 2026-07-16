"""Cross-project feedback read + multilingual search REST routes (``/app/*``).

Session-authenticated (``require_user``) surface that lets a signed-in user
**read and search** feedback across **all their tenant's projects** at once:
list/search, get-one (+comments+attachments), and attachment download. It is
**read + search only** — management (edit/delete/comment) stays on the
project-credential ``/api/project/feedback`` surface (P3.S2).

Scoping mirrors the rest of ``/app/*`` (:mod:`vocky.app_api`): every handler
begins with ``ctx = await require_user(request)``; the caller's project set is
resolved from ``list_projects_for_tenant(ctx.tenant.id)``; any feedback outside
that set answers **404 (never 403)** so cross-tenant existence never leaks. These
routes live outside both ``/api/*`` middlewares — a raised ``AuthError`` is
rendered as a generic 401 by the app-wide handler registered in ``create_app()``.

Search (``?q=``) is a case-insensitive substring (``ILIKE``) filter, newest-first
— **not** relevance ranking — that composes with the standard filters and keyset
paging. It is language-agnostic (Korean 조사-attached forms + English), backed by
a ``pg_trgm`` trigram GIN index (migration ``20260716_1600``); see decision
D-P3-4.
"""

from __future__ import annotations

import logging
from uuid import UUID

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.accounts import get_accounts_service
from vocky.accounts.auth import AuthContext, require_user
from vocky.admin_api import normalize_list_query, parse_attachment_id, parse_feedback_id
from vocky.feedback import (
    FeedbackEventRecord,
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
    normalize_optional_text,
    serialize_attachment,
    serialize_comment,
    serialize_record,
)

logger = logging.getLogger(__name__)


def _serialize_app_record(record: FeedbackEventRecord) -> dict[str, object]:
    """Serialize a feedback record for the cross-project ``/app/*`` surface.

    Reuses the shared serializer, augmented with ``project_id`` — the caller has
    many projects, so the record must say which one it belongs to (unlike the
    single-project ``/api/*`` surface).
    """

    return {
        **serialize_record(record),
        "project_id": str(record.project_id) if record.project_id else None,
    }


async def _owned_project_ids(ctx: AuthContext) -> set[UUID]:
    """Return the id set of every project owned by the caller's tenant."""

    projects = await get_accounts_service().list_projects_for_tenant(ctx.tenant.id)
    return {project.id for project in projects}


async def _resolve_search_scope(
    request: Request, ctx: AuthContext
) -> tuple[UUID, ...] | JSONResponse:
    """Resolve the project-id scope for a cross-project list/search.

    Without ``?project_id`` the scope is every project the tenant owns (possibly
    empty). With ``?project_id`` it narrows to that single project after
    membership validation: a malformed id is 400, and one the caller does not own
    is 404 (never 403) so cross-tenant existence never leaks.
    """

    owned = await _owned_project_ids(ctx)

    raw = request.query_params.get("project_id")
    if raw is None:
        return tuple(owned)

    try:
        narrow = UUID(raw.strip())
    except ValueError:
        return JSONResponse(
            {"detail": "project_id must be a valid UUID"}, status_code=400
        )

    if narrow not in owned:
        return JSONResponse({"detail": "project not found"}, status_code=404)

    return (narrow,)


async def _load_scoped_feedback(
    feedback_id: UUID,
    owned_ids: set[UUID],
) -> FeedbackEventRecord | None:
    """Load a feedback record only when its project is in the caller's tenant.

    Returns ``None`` both when the record is missing and when its ``project_id``
    is outside ``owned_ids`` (including legacy NULL-project rows) — callers turn
    ``None`` into a 404 so cross-tenant existence never leaks. May raise
    :class:`FeedbackReadError`; callers map that to a 500.
    """

    record = await get_feedback_service().get_feedback_event(feedback_id)
    if record is None or record.project_id not in owned_ids:
        return None
    return record


async def list_app_feedback(request: Request) -> JSONResponse:
    """List/search feedback across all the caller's tenant's projects."""

    ctx = await require_user(request)

    try:
        query = normalize_list_query(request)
        query.filters.search = normalize_optional_text(request.query_params.get("q"))
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    scope = await _resolve_search_scope(request, ctx)
    if isinstance(scope, JSONResponse):
        return scope

    # No projects (or a tenant with none) → empty page; never query with an
    # empty id set.
    if not scope:
        return JSONResponse({"records": []})

    query.filters.project_ids = scope

    try:
        page = await get_feedback_service().list_feedback(query)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload: dict[str, object] = {
        "records": [_serialize_app_record(record) for record in page.records],
    }
    if page.next_cursor is not None:
        payload["next_cursor"] = encode_cursor(page.next_cursor)

    return JSONResponse(payload)


async def get_app_feedback(request: Request) -> Response:
    """Return one feedback record (+comments+attachments) from the caller's tenant."""

    ctx = await require_user(request)

    try:
        feedback_id = parse_feedback_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    owned = await _owned_project_ids(ctx)

    try:
        record = await _load_scoped_feedback(feedback_id, owned)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    if record is None:
        return JSONResponse({"detail": "feedback not found"}, status_code=404)

    try:
        comments = await get_feedback_service().list_feedback_comments(feedback_id)
        attachments = await get_feedback_service().list_feedback_attachments(feedback_id)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    payload = _serialize_app_record(record)
    payload["comments"] = [serialize_comment(comment) for comment in comments]
    payload["attachments"] = [
        serialize_attachment(
            attachment,
            url=f"/app/feedback/{feedback_id}/attachments/{attachment.id}",
        )
        for attachment in attachments
    ]
    return JSONResponse({"record": payload})


async def download_app_feedback_attachment(request: Request) -> Response:
    """Stream one attachment linked to a feedback record in the caller's tenant.

    The parent feedback is tenant-verified first (404 on cross-tenant); the
    attachment must be linked to that feedback, else 404.
    """

    ctx = await require_user(request)

    try:
        feedback_id = parse_feedback_id(request)
        attachment_id = parse_attachment_id(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    owned = await _owned_project_ids(ctx)

    try:
        record = await _load_scoped_feedback(feedback_id, owned)
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


# Register the ``/attachments/{id}`` route before the bare ``/{feedback_id}``
# route so Starlette's first-match resolves them correctly.
routes = [
    Route("/app/feedback", list_app_feedback, methods=["GET"]),
    Route(
        "/app/feedback/{feedback_id}/attachments/{attachment_id}",
        download_app_feedback_attachment,
        methods=["GET"],
    ),
    Route("/app/feedback/{feedback_id}", get_app_feedback, methods=["GET"]),
]
