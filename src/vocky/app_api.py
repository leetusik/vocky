"""Account-scoped control-plane routes: the caller's tenant, projects, and keys.

User-authenticated ``/app/*`` surface (outside ``/api/*`` so neither the
public-ingest nor the admin middleware guards it). Every handler begins with
``ctx = await require_user(request)``; a raised ``AuthError`` is rendered as a
generic 401 by the app-wide handler registered in ``create_app()``. Project
reads are scoped to the caller's tenant: a project that is missing *or* owned by
another tenant answers 404, so cross-tenant existence never leaks. Credential
endpoints mint a per-project ingest key whose plaintext value is returned once
(on create) and never persisted or re-exposed.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from vocky.accounts import (
    CreateProject,
    CreateProjectCredential,
    ProjectCredentialRecord,
    ProjectRecord,
    get_accounts_service,
)
from vocky.accounts.auth import AuthContext, require_user
from vocky.accounts.security import generate_opaque_token, sha256_hex
from vocky.api import format_pydantic_error
from vocky.auth_api import serialize_tenant


class AppAPIValidationError(ValueError):
    """Raised when an ``/app/*`` request body or path parameter is invalid."""


class CreateProjectInput(BaseModel):
    """Project-creation request body."""

    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class CreateCredentialInput(BaseModel):
    """Credential-creation request body. ``name`` is an optional display label."""

    name: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


def serialize_project(record: ProjectRecord) -> dict[str, object]:
    """Serialize a project for a response."""

    return {
        "id": str(record.id),
        "name": record.name,
        "tenant_id": str(record.tenant_id),
        "created_at": record.created_at.isoformat(),
    }


def serialize_credential(record: ProjectCredentialRecord) -> dict[str, object]:
    """Serialize a project credential's metadata (never exposes ``token_hash``)."""

    return {
        "id": str(record.id),
        "project_id": str(record.project_id),
        "name": record.name,
        "token_prefix": record.token_prefix,
        "created_at": record.created_at.isoformat(),
        "last_used_at": (
            record.last_used_at.isoformat() if record.last_used_at is not None else None
        ),
        "revoked_at": (
            record.revoked_at.isoformat() if record.revoked_at is not None else None
        ),
    }


async def _parse_body(request: Request, model: type[BaseModel]) -> BaseModel:
    """Parse and validate a JSON object body into ``model``."""

    try:
        raw_body = await request.json()
    except json.JSONDecodeError as exc:
        raise AppAPIValidationError("request body must be valid JSON") from exc

    if not isinstance(raw_body, dict):
        raise AppAPIValidationError("request body must be a JSON object")

    try:
        return model.model_validate(raw_body)
    except ValidationError as exc:
        raise AppAPIValidationError(format_pydantic_error(exc)) from exc


async def _parse_optional_body(request: Request, model: type[BaseModel]) -> BaseModel:
    """Parse an optional JSON object body; an empty body yields model defaults."""

    raw = (await request.body()).strip()
    if not raw:
        return model()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppAPIValidationError("request body must be valid JSON") from exc

    if not isinstance(parsed, dict):
        raise AppAPIValidationError("request body must be a JSON object")

    try:
        return model.model_validate(parsed)
    except ValidationError as exc:
        raise AppAPIValidationError(format_pydantic_error(exc)) from exc


async def _load_scoped_project(
    request: Request, ctx: AuthContext
) -> ProjectRecord | JSONResponse:
    """Resolve ``project_id`` scoped to the caller's tenant.

    Returns the project, or an error response: 400 on a malformed id, and 404
    both when the project is missing and when it belongs to another tenant, so
    cross-tenant existence never leaks.
    """

    try:
        project_id = UUID(request.path_params["project_id"])
    except ValueError:
        return JSONResponse(
            {"detail": "project_id must be a valid UUID"}, status_code=400
        )

    project = await get_accounts_service().get_project(project_id)
    if project is None or project.tenant_id != ctx.tenant.id:
        return JSONResponse({"detail": "project not found"}, status_code=404)

    return project


async def get_tenant(request: Request) -> JSONResponse:
    """Return the authenticated caller's active tenant."""

    ctx = await require_user(request)
    return JSONResponse({"tenant": serialize_tenant(ctx.tenant)}, status_code=200)


async def list_projects(request: Request) -> JSONResponse:
    """Return the caller's tenant's projects, oldest-first."""

    ctx = await require_user(request)
    projects = await get_accounts_service().list_projects_for_tenant(ctx.tenant.id)
    return JSONResponse(
        {"projects": [serialize_project(project) for project in projects]},
        status_code=200,
    )


async def create_project(request: Request) -> JSONResponse:
    """Create a project under the caller's tenant."""

    ctx = await require_user(request)

    try:
        payload = await _parse_body(request, CreateProjectInput)
    except AppAPIValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    project = await get_accounts_service().create_project(
        CreateProject(tenant_id=ctx.tenant.id, name=payload.name)
    )
    return JSONResponse({"project": serialize_project(project)}, status_code=201)


async def get_project(request: Request) -> JSONResponse:
    """Return one of the caller's tenant's projects by id.

    Answers 404 both when the project is missing and when it belongs to another
    tenant, so a caller can never probe another tenant's project ids.
    """

    ctx = await require_user(request)

    try:
        project_id = UUID(request.path_params["project_id"])
    except ValueError:
        return JSONResponse(
            {"detail": "project_id must be a valid UUID"}, status_code=400
        )

    project = await get_accounts_service().get_project(project_id)
    if project is None or project.tenant_id != ctx.tenant.id:
        return JSONResponse({"detail": "project not found"}, status_code=404)

    return JSONResponse({"project": serialize_project(project)}, status_code=200)


async def create_credential(request: Request) -> JSONResponse:
    """Mint a per-project ingest credential; the plaintext key is returned once.

    The raw ``vk_``-prefixed key is emitted only in this response; only its
    sha256 hash (and a short display prefix) is persisted, so it can never be
    recovered afterward.
    """

    ctx = await require_user(request)
    project = await _load_scoped_project(request, ctx)
    if isinstance(project, JSONResponse):
        return project

    try:
        payload = await _parse_optional_body(request, CreateCredentialInput)
    except AppAPIValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    key = f"vk_{generate_opaque_token()}"
    record = await get_accounts_service().create_project_credential(
        CreateProjectCredential(
            project_id=project.id,
            token_prefix=key[:12],
            token_hash=sha256_hex(key),
            name=payload.name,
        )
    )
    return JSONResponse(
        {"credential": serialize_credential(record), "key": key},
        status_code=201,
    )


async def list_credentials(request: Request) -> JSONResponse:
    """List a project's credentials (metadata only, oldest-first)."""

    ctx = await require_user(request)
    project = await _load_scoped_project(request, ctx)
    if isinstance(project, JSONResponse):
        return project

    credentials = await get_accounts_service().list_project_credentials(project.id)
    return JSONResponse(
        {"credentials": [serialize_credential(record) for record in credentials]},
        status_code=200,
    )


async def delete_credential(request: Request) -> Response:
    """Revoke one of a project's credentials by id.

    Answers 404 when the credential does not belong to the scoped project, so a
    caller cannot revoke or probe another project's credential ids.
    """

    ctx = await require_user(request)
    project = await _load_scoped_project(request, ctx)
    if isinstance(project, JSONResponse):
        return project

    try:
        credential_id = UUID(request.path_params["credential_id"])
    except ValueError:
        return JSONResponse(
            {"detail": "credential_id must be a valid UUID"}, status_code=400
        )

    service = get_accounts_service()
    credentials = await service.list_project_credentials(project.id)
    if not any(record.id == credential_id for record in credentials):
        return JSONResponse({"detail": "credential not found"}, status_code=404)

    await service.revoke_credential(credential_id)
    return Response(status_code=204)


routes = [
    Route("/app/tenant", get_tenant, methods=["GET"]),
    Route("/app/projects", list_projects, methods=["GET"]),
    Route("/app/projects", create_project, methods=["POST"]),
    Route("/app/projects/{project_id}", get_project, methods=["GET"]),
    Route(
        "/app/projects/{project_id}/credentials",
        create_credential,
        methods=["POST"],
    ),
    Route(
        "/app/projects/{project_id}/credentials",
        list_credentials,
        methods=["GET"],
    ),
    Route(
        "/app/projects/{project_id}/credentials/{credential_id}",
        delete_credential,
        methods=["DELETE"],
    ),
]
