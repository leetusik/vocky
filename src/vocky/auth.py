"""HTTP authentication helpers."""

from __future__ import annotations

import secrets

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def is_mcp_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the MCP endpoint."""

    return path == "/mcp" or path.startswith("/mcp/")


def is_admin_api_path(path: str) -> bool:
    """Return whether an HTTP path belongs to the Admin REST API."""

    return path == "/admin/api" or path.startswith("/admin/api/")


def is_authorized_bearer(authorization: str | None, expected_token: str) -> bool:
    """Validate a bearer Authorization header against the configured token."""

    if not authorization:
        return False

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return False

    return secrets.compare_digest(token, expected_token)


class MCPBearerAuthMiddleware:
    """Require bearer auth for MCP HTTP traffic when a token is configured."""

    def __init__(self, app: ASGIApp, token: str = "") -> None:
        self.app = app
        self.token = token.strip()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            self.token
            and scope["type"] == "http"
            and is_mcp_path(str(scope.get("path", "")))
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
