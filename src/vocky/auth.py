"""HTTP authentication helpers."""

from __future__ import annotations

import logging
import secrets
from uuid import UUID

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from vocky.accounts.security import sha256_hex
from vocky.accounts.service import (
    AccountsPersistenceError,
    AccountsReadError,
    get_accounts_service,
)
from vocky.accounts.types import ProjectCredentialRecord

logger = logging.getLogger(__name__)

#: ASGI scope key under which the ingest middleware stashes the resolved
#: per-project credential. Namespaced so it is immune to any Starlette
#: ``scope["state"]`` (re)initialization inside the middleware stack.
PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"

#: ASGI scope key under which the ingest middleware stashes the credential's
#: **resolved project-id scope** — the set of projects the credential may read
#: and write. Sibling of :data:`PROJECT_CREDENTIAL_SCOPE_KEY` and namespaced for
#: the same reason.
CREDENTIAL_PROJECT_IDS_SCOPE_KEY = "vocky.credential_project_ids"


def is_admin_api_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the Admin REST API."""

    return path == "/admin/api" or path.startswith("/admin/api/")


def is_api_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the public REST API."""

    return path == "/api" or path.startswith("/api/")


def is_mcp_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the public MCP transport."""

    return path == "/mcp" or path.startswith("/mcp/")


def is_authorized_bearer(authorization: str | None, expected_token: str) -> bool:
    """Validate a bearer Authorization header against the configured token."""

    if not authorization:
        return False

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return False

    return secrets.compare_digest(token, expected_token)


def extract_bearer_credential(authorization: str | None) -> str | None:
    """Return the bearer credential from an ``Authorization`` header, or None.

    Scheme-insensitive on ``Bearer``; returns None when the header is absent or
    is not a well-formed, non-empty bearer credential.
    """

    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None

    token = token.strip()
    return token or None


class AdminBearerAuthMiddleware:
    """Require bearer auth for Admin REST traffic; fail closed with no token.

    A missing ``VOCKY_ADMIN_AUTH_TOKEN`` is a server misconfiguration, not an
    "open" state: every ``/admin/api/*`` request is refused with ``503`` until
    an operator configures a token. This is deliberate defense in depth — the
    Admin REST surface must never be reachable purely because a deploy forgot
    to set a box secret.
    """

    def __init__(self, app: ASGIApp, token: str = "") -> None:
        self.app = app
        self.token = token.strip()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and is_admin_api_path(str(scope.get("path", ""))):
            if not self.token:
                response = JSONResponse(
                    {"detail": "Admin API is not configured"},
                    status_code=503,
                )
                await response(scope, receive, send)
                return

            if not is_authorized_bearer(
                dict(scope.get("headers", [])).get(b"authorization", b"").decode("latin1"),
                self.token,
            ):
                response = JSONResponse(
                    {"detail": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


async def resolve_credential_project_ids(
    credential: ProjectCredentialRecord,
) -> tuple[UUID, ...]:
    """Return the project-id scope a credential authorizes, never ``None``.

    A **project-bound** credential (``project_id`` set) resolves to exactly its
    own project with **no database call**, so today's hot ingest path costs
    exactly what it costs today. An **org-level** credential (``project_id IS
    NULL``, P10) resolves to every project its tenant owns — one extra indexed
    SELECT, on a request that already does two round trips.

    The ``tuple`` return type is the enforcement: ``FeedbackQueryFilters``
    reads ``None`` as *"no filter"* rather than *"no rows"*
    (:meth:`vocky.feedback.repository.FeedbackRepository._apply_query_filters`),
    so a nullable scope would fail **open** to a global, cross-tenant read. An
    empty tuple is a legitimate answer (an org with no projects) and callers
    must short-circuit it to an empty result rather than query with it.

    Deliberately not cached across requests: a revoked credential or a deleted
    project must take effect immediately, and this repo has no cache layer to
    reuse. It is memoized *per request* by the middleware stashing the result.
    """

    if credential.project_id is not None:
        return (credential.project_id,)

    projects = await get_accounts_service().list_projects_for_tenant(
        credential.tenant_id
    )
    return tuple(project.id for project in projects)


class ProjectCredentialAuthMiddleware:
    """Require a valid, non-revoked ingest credential for public ingest traffic.

    Ingest auth on ``/api/*`` **and** ``/mcp`` (the whole MCP transport, including
    ``initialize``) is strictly mandatory: every request must present a bearer
    token that resolves to an active project credential. Missing, malformed,
    unknown, and revoked keys all answer a generic 401. On success the resolved
    ``ProjectCredentialRecord`` is stashed under ``PROJECT_CREDENTIAL_SCOPE_KEY``
    so handlers (REST via ``get_request_credential``, MCP tools via the same
    helper off ``ctx.request_context.request``) can scope capture to the
    credential's project, and the credential's ``last_used_at`` is stamped
    best-effort. A stamping failure never turns a valid ingest request into a 500.

    The credential's **project scope** is resolved once here too and stashed
    under ``CREDENTIAL_PROJECT_IDS_SCOPE_KEY`` (read back with
    :func:`get_request_project_ids`). Resolving it in one place rather than per
    handler is the whole safety argument: there are ten credential-scoped call
    sites across four modules, and a single missed one is a silent cross-tenant
    read rather than an error. Unlike the best-effort ``last_used_at`` stamp,
    a scope-resolution failure fails **closed** with a 500 — never an unscoped
    read.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and (
            is_api_path(str(scope.get("path", "")))
            or is_mcp_path(str(scope.get("path", "")))
        ):
            authorization = (
                dict(scope.get("headers", []))
                .get(b"authorization", b"")
                .decode("latin1")
            )
            token = extract_bearer_credential(authorization)
            credential = (
                await get_accounts_service().get_active_credential_by_token_hash(
                    sha256_hex(token)
                )
                if token is not None
                else None
            )
            if credential is None:
                response = JSONResponse(
                    {"detail": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return

            scope[PROJECT_CREDENTIAL_SCOPE_KEY] = credential

            # Resolve the credential's project scope once per request. Fails
            # closed: an unresolvable scope answers 500 rather than letting a
            # handler fall through to an unfiltered (cross-tenant) read.
            try:
                scope[CREDENTIAL_PROJECT_IDS_SCOPE_KEY] = (
                    await resolve_credential_project_ids(credential)
                )
            except AccountsReadError:
                logger.exception(
                    "failed to resolve project scope for credential %s",
                    credential.id,
                )
                response = JSONResponse(
                    {"detail": "credential scope unavailable"}, status_code=500
                )
                await response(scope, receive, send)
                return

            # Best-effort usage stamp (one indexed UPDATE by PK). Never let a
            # stamping failure turn a valid ingest into a 500; a throttle is a
            # possible future optimization if this write becomes hot.
            try:
                await get_accounts_service().touch_credential_last_used(credential.id)
            except AccountsPersistenceError:
                logger.warning(
                    "failed to stamp last_used_at for credential %s",
                    credential.id,
                    exc_info=True,
                )

        await self.app(scope, receive, send)


def get_request_credential(request: Request) -> ProjectCredentialRecord:
    """Return the per-project credential the ingest middleware resolved.

    Only valid for ``/api/*`` and ``/mcp`` requests that passed
    ``ProjectCredentialAuthMiddleware`` (both now carry the resolved credential on
    the ASGI scope); the record carries ``.id``, ``.tenant_id``, and
    ``.project_id`` (``None`` ⇒ org-level). **To scope a read or a write, use
    :func:`get_request_project_ids`, not ``.project_id``** — the latter is
    nullable and a ``None`` project filter reads every project in every tenant.
    """

    return request.scope[PROJECT_CREDENTIAL_SCOPE_KEY]


def get_request_project_ids(request: Request) -> tuple[UUID, ...]:
    """Return the project-id scope the ingest middleware resolved, never ``None``.

    The single source of project scope for every credential-authenticated
    handler: one element for today's project-bound key, the tenant's whole
    project set for an org-level key (P10). Raises ``KeyError`` when
    ``ProjectCredentialAuthMiddleware`` did not run, exactly like
    :func:`get_request_credential` — an unscoped read is never a silent outcome.

    An **empty** tuple (an org that owns no projects) is a valid answer and must
    be short-circuited to an empty result: never pass it to a query, because
    ``FeedbackQueryFilters`` cannot express "no rows" through an absent filter.
    """

    return request.scope[CREDENTIAL_PROJECT_IDS_SCOPE_KEY]
