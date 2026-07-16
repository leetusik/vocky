"""HTTP authentication helpers."""

from __future__ import annotations

import secrets

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from vocky.accounts.security import sha256_hex
from vocky.accounts.service import get_accounts_service


def is_admin_api_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the Admin REST API."""

    return path == "/admin/api" or path.startswith("/admin/api/")


def is_api_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the public REST API."""

    return path == "/api" or path.startswith("/api/")


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
    """Require a valid, non-revoked per-project credential for public REST traffic.

    Ingest auth on ``/api/*`` is strictly mandatory: every request must present a
    bearer token that resolves to an active project credential. Missing,
    malformed, unknown, and revoked keys all answer a generic 401. This layer is
    identity-only -- it authenticates the request but does not stash project
    state onto the scope (threading project scope into capture is P3).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and is_api_path(str(scope.get("path", ""))):
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

        await self.app(scope, receive, send)
