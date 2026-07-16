"""HTTP authentication helpers."""

from __future__ import annotations

import logging
import secrets

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from vocky.accounts.security import sha256_hex
from vocky.accounts.service import AccountsPersistenceError, get_accounts_service
from vocky.accounts.types import ProjectCredentialRecord

logger = logging.getLogger(__name__)

#: ASGI scope key under which the ingest middleware stashes the resolved
#: per-project credential. Namespaced so it is immune to any Starlette
#: ``scope["state"]`` (re)initialization inside the middleware stack.
PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"


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
    """Require bearer auth for Admin REST traffic when a token is configured."""

    def __init__(self, app: ASGIApp, token: str = "") -> None:
        self.app = app
        self.token = token.strip()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            self.token
            and scope["type"] == "http"
            and is_admin_api_path(str(scope.get("path", "")))
            and not is_authorized_bearer(
                dict(scope.get("headers", [])).get(b"authorization", b"").decode("latin1"),
                self.token,
            )
        ):
            response = JSONResponse(
                {"detail": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class ProjectCredentialAuthMiddleware:
    """Require a valid, non-revoked per-project credential for public ingest traffic.

    Ingest auth on ``/api/*`` **and** ``/mcp`` (the whole MCP transport, including
    ``initialize``) is strictly mandatory: every request must present a bearer
    token that resolves to an active project credential. Missing, malformed,
    unknown, and revoked keys all answer a generic 401. On success the resolved
    ``ProjectCredentialRecord`` is stashed under ``PROJECT_CREDENTIAL_SCOPE_KEY``
    so handlers (REST via ``get_request_credential``, MCP tools via the same
    helper off ``ctx.request_context.request``) can scope capture to the
    credential's project, and the credential's ``last_used_at`` is stamped
    best-effort. A stamping failure never turns a valid ingest request into a 500.
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
    the ASGI scope); the record carries ``.id`` and ``.project_id`` for
    project-scoping capture and reads.
    """

    return request.scope[PROJECT_CREDENTIAL_SCOPE_KEY]
