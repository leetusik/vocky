"""Reusable user-auth guard for account-scoped routes.

``require_user`` resolves an opaque ``Authorization: Bearer`` token to the
active user plus their (solo-owner MVP) tenant, raising ``AuthError`` on any
miss. S3/S4 import ``require_user`` / ``AuthContext`` / ``AuthError`` from here;
``auth_error_handler`` renders the shared generic 401. On a successful token
resolve it stamps the token's ``last_used_at`` best-effort — a stamping failure
is logged and never fails auth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import JSONResponse

from vocky.accounts.security import sha256_hex
from vocky.accounts.service import AccountsPersistenceError, get_accounts_service
from vocky.accounts.types import TenantRecord, UserRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuthContext:
    """The authenticated caller: their user record and active tenant."""

    user: UserRecord
    tenant: TenantRecord


class AuthError(Exception):
    """Raised when a request cannot be authenticated as a user.

    Rendered by ``auth_error_handler`` as a generic 401 so no distinction
    between missing, unknown, and expired tokens leaks to the caller.
    """


def extract_bearer_token(request: Request) -> str | None:
    """Return the bearer token from the ``Authorization`` header, or None.

    Scheme-insensitive on ``Bearer``; returns None when the header is absent or
    not a well-formed bearer credential.
    """

    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None

    token = token.strip()
    return token or None


async def require_user(request: Request) -> AuthContext:
    """Resolve the request's bearer token to an ``AuthContext`` or raise.

    Extract the token, hash it, look up the active session, load the user, and
    pick their first tenant. Any miss raises ``AuthError`` (generic 401).
    """

    token = extract_bearer_token(request)
    if token is None:
        raise AuthError("missing bearer token")

    service = get_accounts_service()
    token_hash = sha256_hex(token)
    auth_token = await service.get_active_auth_token_by_hash(token_hash)
    if auth_token is None:
        raise AuthError("invalid or expired token")

    # Best-effort usage stamp (one indexed UPDATE by token_hash); a failure is
    # logged and must never fail auth.
    try:
        await service.touch_auth_token_last_used(token_hash)
    except AccountsPersistenceError:
        logger.warning("failed to stamp last_used_at for auth token", exc_info=True)

    user = await service.get_user_by_id(auth_token.user_id)
    if user is None:
        raise AuthError("token references a missing user")

    tenants = await service.list_tenants_for_user(user.id)
    if not tenants:
        raise AuthError("user has no tenant")

    return AuthContext(user=user, tenant=tenants[0])


async def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render ``AuthError`` as a generic 401 with a bearer challenge."""

    return JSONResponse(
        {"detail": "Unauthorized"},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )
