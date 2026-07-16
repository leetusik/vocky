"""Account-scoped control-plane REST tests (`/app/tenant`, `/app/projects`)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from starlette.applications import Starlette

from vocky.accounts import get_accounts_service
from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.accounts.security import sha256_hex
from vocky.app_api import routes as app_api_routes
from vocky.auth_api import routes as auth_routes


def make_app() -> Starlette:
    """Create a test app with auth + control-plane routes and the 401 handler."""

    return Starlette(
        routes=[*auth_routes, *app_api_routes],
        exception_handlers={AuthError: auth_error_handler},
    )


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=make_app())
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _signup(client: httpx.AsyncClient, email: str) -> str:
    response = await client.post(
        "/auth/signup", json={"email": email, "password": "hunter2pass"}
    )
    assert response.status_code == 201
    return response.json()["token"]


@pytest.mark.anyio
async def test_create_list_and_get_project(configured_database: str) -> None:
    async with _client() as client:
        token = await _signup(client, "alice@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/app/projects", json={"name": "  Website  "}, headers=headers
        )
        listed = await client.get("/app/projects", headers=headers)

        assert created.status_code == 201
        project = created.json()["project"]
        assert project["name"] == "Website"  # stripped
        assert project["tenant_id"]
        project_id = project["id"]

        fetched = await client.get(f"/app/projects/{project_id}", headers=headers)

    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()["projects"]] == [project_id]

    assert fetched.status_code == 200
    assert fetched.json()["project"]["id"] == project_id


@pytest.mark.anyio
async def test_get_project_cross_tenant_returns_404(configured_database: str) -> None:
    async with _client() as client:
        owner_token = await _signup(client, "owner@example.com")
        created = await client.post(
            "/app/projects",
            json={"name": "Secret"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        project_id = created.json()["project"]["id"]

        other_token = await _signup(client, "intruder@example.com")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        cross = await client.get(f"/app/projects/{project_id}", headers=other_headers)
        other_list = await client.get("/app/projects", headers=other_headers)

    # Cross-tenant read answers 404 (never 403): no existence leak.
    assert cross.status_code == 404
    # The intruder's own project list is empty — full tenant isolation.
    assert other_list.json()["projects"] == []


@pytest.mark.anyio
async def test_get_tenant_returns_callers_tenant(configured_database: str) -> None:
    async with _client() as client:
        token = await _signup(client, "carol@example.com")
        response = await client.get(
            "/app/tenant", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert response.json()["tenant"]["name"] == "carol's workspace"


@pytest.mark.anyio
async def test_authed_app_call_stamps_auth_token_last_used(
    configured_database: str,
) -> None:
    async with _client() as client:
        token = await _signup(client, "stamp@example.com")
        # Signup issues the token but require_user has not run yet.
        before = await get_accounts_service().get_active_auth_token_by_hash(
            sha256_hex(token)
        )
        assert before is not None
        assert before.last_used_at is None

        response = await client.get(
            "/app/tenant", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    after = await get_accounts_service().get_active_auth_token_by_hash(
        sha256_hex(token)
    )
    assert after is not None
    assert after.last_used_at is not None


@pytest.mark.anyio
async def test_app_routes_require_auth(configured_database: str) -> None:
    async with _client() as client:
        no_token = await client.get("/app/projects")
        bad_token = await client.get(
            "/app/tenant", headers={"Authorization": "Bearer nope"}
        )

    assert no_token.status_code == 401
    assert no_token.json() == {"detail": "Unauthorized"}
    assert no_token.headers["www-authenticate"] == "Bearer"
    assert bad_token.status_code == 401


@pytest.mark.anyio
async def test_create_project_rejects_blank_name(configured_database: str) -> None:
    async with _client() as client:
        token = await _signup(client, "dave@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        blank = await client.post("/app/projects", json={"name": "   "}, headers=headers)
        missing = await client.post("/app/projects", json={}, headers=headers)

    assert blank.status_code == 400
    assert missing.status_code == 400


@pytest.mark.anyio
async def test_get_project_malformed_id_returns_400(configured_database: str) -> None:
    async with _client() as client:
        token = await _signup(client, "erin@example.com")
        malformed = await client.get(
            "/app/projects/not-a-uuid",
            headers={"Authorization": f"Bearer {token}"},
        )
        # A well-formed but unknown id is 404 (missing), not 400.
        unknown = await client.get(
            f"/app/projects/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert malformed.status_code == 400
    assert unknown.status_code == 404
