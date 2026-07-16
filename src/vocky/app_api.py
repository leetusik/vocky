"""Account-scoped control-plane routes: the caller's tenant and projects.

User-authenticated ``/app/*`` surface (outside ``/api/*`` so neither the
public-ingest nor the admin middleware guards it). Every handler begins with
``ctx = await require_user(request)``; a raised ``AuthError`` is rendered as a
generic 401 by the app-wide handler registered in ``create_app()``. Project
reads are scoped to the caller's tenant: a project that is missing *or* owned by
another tenant answers 404, so cross-tenant existence never leaks.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vocky.accounts import CreateProject, ProjectRecord, get_accounts_service
from vocky.accounts.auth import require_user
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


def serialize_project(record: ProjectRecord) -> dict[str, object]:
    """Serialize a project for a response."""

    return {
        "id": str(record.id),
        "name": record.name,
        "tenant_id": str(record.tenant_id),
        "created_at": record.created_at.isoformat(),
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


routes = [
    Route("/app/tenant", get_tenant, methods=["GET"]),
    Route("/app/projects", list_projects, methods=["GET"]),
    Route("/app/projects", create_project, methods=["POST"]),
    Route("/app/projects/{project_id}", get_project, methods=["GET"]),
]
