"""Account auth routes: signup, login, logout, and the caller's identity.

Public ``/auth/*`` surface (outside ``/api/*`` so the public-ingest middleware
never guards it). Signup provisions a user, a tenant, and the owner membership,
then mints an opaque DB-backed bearer token; login re-issues one. Raw tokens are
returned once and stored only as a sha256 hash. Responses never expose
``password_hash`` or any ``token_hash``.
"""

from __future__ import annotations

import json
from datetime import timedelta

from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.accounts import (
    CreateAuthToken,
    CreateUser,
    DuplicateEmailError,
    TenantRecord,
    UserRecord,
    get_accounts_service,
)
from vocky.accounts.auth import AuthContext, extract_bearer_token, require_user
from vocky.accounts.security import (
    generate_opaque_token,
    hash_password,
    sha256_hex,
    verify_password,
)
from vocky.api import format_pydantic_error
from vocky.persistence.models import utc_now

SESSION_TTL = timedelta(days=30)

# Identical generic 401 for unknown-email vs bad-password (no user enumeration).
_INVALID_CREDENTIALS = {"detail": "invalid email or password"}


class AuthAPIValidationError(ValueError):
    """Raised when an auth request body is invalid."""


class _EmailPasswordInput(BaseModel):
    """Shared email + password shape for signup and login."""

    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("must not be blank")
        if "@" not in normalized:
            raise ValueError("must be a valid email address")
        return normalized


class SignupInput(_EmailPasswordInput):
    """Signup request body."""


class LoginInput(_EmailPasswordInput):
    """Login request body."""


def serialize_user(record: UserRecord) -> dict[str, object]:
    """Serialize a user for a response (never exposes ``password_hash``)."""

    return {
        "id": str(record.id),
        "email": record.email,
        "created_at": record.created_at.isoformat(),
    }


def serialize_tenant(record: TenantRecord) -> dict[str, object]:
    """Serialize a tenant for a response."""

    return {
        "id": str(record.id),
        "name": record.name,
        "created_at": record.created_at.isoformat(),
    }


async def _parse_body(request: Request, model: type[BaseModel]) -> BaseModel:
    """Parse and validate a JSON object body into ``model``."""

    try:
        raw_body = await request.json()
    except json.JSONDecodeError as exc:
        raise AuthAPIValidationError("request body must be valid JSON") from exc

    if not isinstance(raw_body, dict):
        raise AuthAPIValidationError("request body must be a JSON object")

    try:
        return model.model_validate(raw_body)
    except ValidationError as exc:
        raise AuthAPIValidationError(format_pydantic_error(exc)) from exc


async def _mint_token(user_id) -> str:
    """Mint an opaque bearer token, store its hash, and return the raw token."""

    raw_token = generate_opaque_token()
    await get_accounts_service().create_auth_token(
        CreateAuthToken(
            user_id=user_id,
            token_hash=sha256_hex(raw_token),
            expires_at=utc_now() + SESSION_TTL,
        )
    )
    return raw_token


async def signup(request: Request) -> JSONResponse:
    """Create a user, their tenant, and owner membership; mint a session token."""

    try:
        payload = await _parse_body(request, SignupInput)
    except AuthAPIValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    service = get_accounts_service()
    try:
        user = await service.create_user(
            CreateUser(email=payload.email, password_hash=hash_password(payload.password))
        )
    except DuplicateEmailError:
        return JSONResponse(
            {"detail": "a user with this email already exists"}, status_code=409
        )

    workspace_name = f"{payload.email.split('@')[0]}'s workspace"
    tenant, _member = await service.create_tenant_with_owner(user.id, workspace_name)
    token = await _mint_token(user.id)

    return JSONResponse(
        {
            "token": token,
            "user": serialize_user(user),
            "tenant": serialize_tenant(tenant),
        },
        status_code=201,
    )


async def login(request: Request) -> JSONResponse:
    """Verify credentials and mint a session token.

    Answers an identical generic 401 for an unknown email and a wrong password
    so callers cannot enumerate registered accounts.
    """

    try:
        payload = await _parse_body(request, LoginInput)
    except AuthAPIValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    service = get_accounts_service()
    user = await service.get_user_by_email(payload.email)
    if user is None or not verify_password(user.password_hash, payload.password):
        return JSONResponse(_INVALID_CREDENTIALS, status_code=401)

    token = await _mint_token(user.id)
    tenants = await service.list_tenants_for_user(user.id)

    return JSONResponse(
        {
            "token": token,
            "user": serialize_user(user),
            "tenants": [serialize_tenant(tenant) for tenant in tenants],
        },
        status_code=200,
    )


async def logout(request: Request) -> Response:
    """Revoke the presented session token (idempotent)."""

    token = extract_bearer_token(request)
    if token is not None:
        await get_accounts_service().delete_auth_token(sha256_hex(token))
    return Response(status_code=204)


async def me(request: Request) -> JSONResponse:
    """Return the authenticated caller and their tenants."""

    context: AuthContext = await require_user(request)
    tenants = await get_accounts_service().list_tenants_for_user(context.user.id)

    return JSONResponse(
        {
            "user": serialize_user(context.user),
            "tenants": [serialize_tenant(tenant) for tenant in tenants],
        },
        status_code=200,
    )


routes = [
    Route("/auth/signup", signup, methods=["POST"]),
    Route("/auth/login", login, methods=["POST"]),
    Route("/auth/logout", logout, methods=["POST"]),
    Route("/auth/me", me, methods=["GET"]),
]
