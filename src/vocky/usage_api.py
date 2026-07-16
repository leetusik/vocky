"""Usage-monitoring REST routes: derived capture volume + surfaced last-used.

Three read-only surfaces expose feedback-capture volume over a time window,
derived **entirely** from the existing feedback metrics query
(:meth:`vocky.feedback.service.FeedbackService.get_feedback_metrics`) scoped by
project — **no new tables, no request-count metering** (decision D-P3-5:
operational visibility, not billing):

- ``GET /app/usage`` (session, :func:`require_user`): the caller's whole-tenant
  capture volume aggregated across every project it owns, plus a light project
  list. An empty tenant short-circuits to zeroed metrics.
- ``GET /app/projects/{project_id}/usage`` (session): one project's capture
  volume plus that project's credentials, surfacing each key's ``last_used_at``
  (the stamp wired in P3.S1). Cross-tenant project ids answer 404.
- ``GET /api/project/usage`` (project ``vk_`` key, guarded by the
  ``ProjectCredentialAuthMiddleware``): the credential's own project's capture
  volume plus its credentials.

Scoping reuses the shared ``_apply_query_filters`` chokepoint: the whole-tenant
call sets :attr:`FeedbackQueryFilters.project_ids` to the tenant's project set,
the per-project calls set :attr:`FeedbackQueryFilters.project_id`. The window
defaults to the last 30 days when both bounds are omitted so a dashboard can call
with no parameters.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vocky.accounts import ProjectRecord, get_accounts_service
from vocky.accounts.auth import require_user
from vocky.admin_api import serialize_metrics
from vocky.app_api import _load_scoped_project, serialize_credential
from vocky.auth import get_request_credential
from vocky.feedback import (
    FeedbackMetricCounts,
    FeedbackMetrics,
    FeedbackMetricsQuery,
    FeedbackQueryFilters,
    FeedbackReadError,
    get_feedback_service,
)
from vocky.persistence.models import utc_now
from vocky.tools.query_feedback_common import (
    FeedbackQueryValidationError,
    parse_timestamp,
    validate_time_window,
)

#: Default lookback when a usage request omits its window bounds.
DEFAULT_USAGE_WINDOW = timedelta(days=30)


def _resolve_usage_window(request: Request) -> tuple[datetime, datetime]:
    """Resolve the usage window, defaulting to the last 30 days.

    Both ``start_ingested_at`` / ``end_ingested_at`` bounds are optional ISO-8601
    timestamps. With both omitted the window is the last 30 days ending now; with
    only one given the other is filled in around it (``end`` = now, or ``start`` =
    ``end`` - 30d) so a partial request stays friendly. Raises
    :class:`FeedbackQueryValidationError` on a malformed bound or an inverted
    window; callers map that to a 400.
    """

    start = parse_timestamp(
        request.query_params.get("start_ingested_at"),
        field_name="start_ingested_at",
    )
    end = parse_timestamp(
        request.query_params.get("end_ingested_at"),
        field_name="end_ingested_at",
    )

    if end is None:
        end = utc_now()
    if start is None:
        start = end - DEFAULT_USAGE_WINDOW

    validate_time_window(start, end)
    return start, end


def _zeroed_metrics() -> FeedbackMetrics:
    """Return an all-zero metrics result for a caller that owns no projects."""

    return FeedbackMetrics(
        totals=FeedbackMetricCounts(total=0, liked=0, disliked=0, unrated=0),
        daily_counts=(),
    )


def _serialize_usage_project(project: ProjectRecord) -> dict[str, object]:
    """Serialize a light project entry for the tenant-aggregate usage overview."""

    return {
        "id": str(project.id),
        "name": project.name,
        "created_at": project.created_at.isoformat(),
    }


async def _project_usage_response(
    project_id: UUID,
    start: datetime,
    end: datetime,
) -> JSONResponse:
    """Build a per-project usage payload: metrics + the project's credentials.

    Shared by the session ``/app/projects/{id}/usage`` drill-down and the
    ``/api/project/usage`` external-panel surface — both report one project's
    derived capture volume plus its credentials (surfacing ``last_used_at``).
    """

    query = FeedbackMetricsQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start,
            end_ingested_at=end,
            project_id=project_id,
        )
    )

    try:
        metrics = await get_feedback_service().get_feedback_metrics(query)
    except FeedbackReadError:
        return JSONResponse({"detail": "storage read failed"}, status_code=500)

    credentials = await get_accounts_service().list_project_credentials(project_id)

    payload = serialize_metrics(metrics, query)
    payload["credentials"] = [serialize_credential(record) for record in credentials]
    return JSONResponse(payload)


async def get_app_usage(request: Request) -> JSONResponse:
    """Return the caller's whole-tenant capture volume + a light project list."""

    ctx = await require_user(request)

    try:
        start, end = _resolve_usage_window(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    projects = await get_accounts_service().list_projects_for_tenant(ctx.tenant.id)
    project_ids = tuple(project.id for project in projects)

    query = FeedbackMetricsQuery(
        filters=FeedbackQueryFilters(
            start_ingested_at=start,
            end_ingested_at=end,
            project_ids=project_ids or None,
        )
    )

    if not project_ids:
        # No projects → zeroed metrics; never query with an empty id set
        # (the S3 empty-scope convention).
        payload = serialize_metrics(_zeroed_metrics(), query)
    else:
        try:
            metrics = await get_feedback_service().get_feedback_metrics(query)
        except FeedbackReadError:
            return JSONResponse({"detail": "storage read failed"}, status_code=500)
        payload = serialize_metrics(metrics, query)

    payload["projects"] = [_serialize_usage_project(project) for project in projects]
    return JSONResponse(payload)


async def get_project_usage(request: Request) -> JSONResponse:
    """Return one owned project's capture volume + its credentials (drill-down)."""

    ctx = await require_user(request)

    project = await _load_scoped_project(request, ctx)
    if isinstance(project, JSONResponse):
        return project

    try:
        start, end = _resolve_usage_window(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    return await _project_usage_response(project.id, start, end)


async def get_api_project_usage(request: Request) -> JSONResponse:
    """Return the authenticating credential's project usage + its credentials."""

    credential = get_request_credential(request)

    try:
        start, end = _resolve_usage_window(request)
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    return await _project_usage_response(credential.project_id, start, end)


routes = [
    Route("/app/usage", get_app_usage, methods=["GET"]),
    Route("/app/projects/{project_id}/usage", get_project_usage, methods=["GET"]),
    Route("/api/project/usage", get_api_project_usage, methods=["GET"]),
]
