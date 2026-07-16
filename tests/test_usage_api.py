"""Usage-monitoring tests: derived capture volume + surfaced last-used.

Covers the three usage surfaces (`/app/usage`, `/app/projects/{id}/usage`,
`/api/project/usage`), tenant aggregation across projects, cross-tenant
isolation, the default 30-day window, and auth (401s). All metrics are derived
from `get_feedback_metrics` — no new tables (D-P3-5).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

from vocky.accounts import get_accounts_service
from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.app_api import routes as app_api_routes
from vocky.auth import ProjectCredentialAuthMiddleware
from vocky.auth_api import routes as auth_routes
from vocky.db import get_engine
from vocky.usage_api import routes as usage_routes

# An explicit window that brackets every June-2026 seed row below.
WINDOW = {
    "start_ingested_at": "2026-06-01T00:00:00Z",
    "end_ingested_at": "2026-07-01T00:00:00Z",
}


def make_app() -> Starlette:
    """Test app: auth + control-plane + usage routes, ingest middleware, 401 handler.

    The ingest middleware guards only `/api/*`, so the `/app/*` routes pass
    through untouched while `/api/project/usage` gets credential auth.
    """

    app = Starlette(
        routes=[*auth_routes, *app_api_routes, *usage_routes],
        exception_handlers={AuthError: auth_error_handler},
    )
    app.add_middleware(ProjectCredentialAuthMiddleware)
    return app


def _client(**headers: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=make_app()),
        base_url="http://testserver",
        headers=headers,
    )


async def _signup(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/auth/signup", json={"email": email, "password": "hunter2pass"}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _make_project(
    client: httpx.AsyncClient, headers: dict[str, str], name: str
) -> str:
    response = await client.post("/app/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["project"]["id"]


async def _seed(
    *,
    project_id: str,
    ingested_at: datetime,
    feedback_value: int | None,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events "
                "(id, message, source_product, feedback_value, ingested_at, project_id) "
                "VALUES (:id, 'row', 'changple5', :feedback_value, :ingested_at, :project_id)"
            ),
            {
                "id": str(uuid4()),
                "feedback_value": feedback_value,
                "ingested_at": ingested_at,
                "project_id": project_id,
            },
        )


@pytest.mark.anyio
async def test_app_usage_aggregates_tenant_and_isolates_other(
    configured_database: str,
) -> None:
    async with _client() as client:
        headers = await _signup(client, "alice@example.com")
        project_a = await _make_project(client, headers, "Project A")
        project_b = await _make_project(client, headers, "Project B")

        june = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
        # Project A: 2 liked + 1 disliked; Project B: 1 liked + 1 unrated.
        for value in (1, 1, 2):
            await _seed(project_id=project_a, ingested_at=june, feedback_value=value)
        for value in (1, None):
            await _seed(project_id=project_b, ingested_at=june, feedback_value=value)

        # A second tenant's feedback must never bleed into the aggregate.
        other = await _signup(client, "intruder@example.com")
        project_x = await _make_project(client, other, "Project X")
        for _ in range(5):
            await _seed(project_id=project_x, ingested_at=june, feedback_value=1)

        usage = await client.get("/app/usage", params=WINDOW, headers=headers)

        # A brand-new tenant with no projects → zeroed metrics, empty project list.
        empty = await _signup(client, "empty@example.com")
        empty_usage = await client.get("/app/usage", params=WINDOW, headers=empty)

    assert usage.status_code == 200
    body = usage.json()
    assert body["totals"] == {"total": 5, "liked": 3, "disliked": 1, "unrated": 1}
    assert {p["id"] for p in body["projects"]} == {project_a, project_b}
    assert {p["name"] for p in body["projects"]} == {"Project A", "Project B"}
    assert "window" in body

    assert empty_usage.status_code == 200
    empty_body = empty_usage.json()
    assert empty_body["totals"] == {"total": 0, "liked": 0, "disliked": 0, "unrated": 0}
    assert empty_body["projects"] == []


@pytest.mark.anyio
async def test_project_usage_drilldown_credentials_and_cross_tenant_404(
    configured_database: str,
) -> None:
    async with _client() as client:
        headers = await _signup(client, "owner@example.com")
        project_a = await _make_project(client, headers, "Project A")
        project_b = await _make_project(client, headers, "Project B")

        june = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
        for value in (1, 2):
            await _seed(project_id=project_a, ingested_at=june, feedback_value=value)
        await _seed(project_id=project_b, ingested_at=june, feedback_value=1)

        # Mint a credential on project A and stamp its last_used_at (the S1 stamp).
        created = await client.post(
            f"/app/projects/{project_a}/credentials", headers=headers
        )
        assert created.status_code == 201
        credential_id = created.json()["credential"]["id"]
        await get_accounts_service().touch_credential_last_used(credential_id)

        # A second tenant with its own project.
        other = await _signup(client, "stranger@example.com")
        project_x = await _make_project(client, other, "Project X")

        drill = await client.get(
            f"/app/projects/{project_a}/usage", params=WINDOW, headers=headers
        )
        cross = await client.get(
            f"/app/projects/{project_x}/usage", params=WINDOW, headers=headers
        )

    assert drill.status_code == 200
    drill_body = drill.json()
    # Only project A's rows are counted (project B excluded).
    assert drill_body["totals"] == {"total": 2, "liked": 1, "disliked": 1, "unrated": 0}
    creds = drill_body["credentials"]
    assert [c["id"] for c in creds] == [credential_id]
    assert creds[0]["last_used_at"] is not None

    # A project owned by another tenant answers 404 (never 403).
    assert cross.status_code == 404


@pytest.mark.anyio
async def test_api_project_usage_scopes_to_credential_project(
    configured_database: str,
    configured_project_credential,
) -> None:
    from vocky.accounts import CreateProject

    # A second project under the same tenant that must NOT be counted.
    other_project = await get_accounts_service().create_project(
        CreateProject(tenant_id=configured_project_credential.tenant_id, name="other")
    )

    june = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    for value in (1, 1, 2):
        await _seed(
            project_id=str(configured_project_credential.project_id),
            ingested_at=june,
            feedback_value=value,
        )
    await _seed(project_id=str(other_project.id), ingested_at=june, feedback_value=1)

    async with _client(
        Authorization=f"Bearer {configured_project_credential.key}"
    ) as client:
        usage = await client.get("/api/project/usage", params=WINDOW)

    assert usage.status_code == 200
    body = usage.json()
    # Only the credential's own project's rows are counted.
    assert body["totals"] == {"total": 3, "liked": 2, "disliked": 1, "unrated": 0}
    assert [c["id"] for c in body["credentials"]] == [
        str(configured_project_credential.credential_id)
    ]


@pytest.mark.anyio
async def test_default_window_covers_last_30_days(configured_database: str) -> None:
    async with _client() as client:
        headers = await _signup(client, "windowed@example.com")
        project = await _make_project(client, headers, "Project")

        recent = datetime.now(UTC) - timedelta(days=1)
        old = datetime.now(UTC) - timedelta(days=60)
        await _seed(project_id=project, ingested_at=recent, feedback_value=1)
        await _seed(project_id=project, ingested_at=old, feedback_value=2)

        default = await client.get("/app/usage", headers=headers)
        wide = await client.get(
            "/app/usage",
            params={
                "start_ingested_at": "2020-01-01T00:00:00Z",
                "end_ingested_at": "2100-01-01T00:00:00Z",
            },
            headers=headers,
        )

    # Default window (last 30 days) counts only the recent row.
    assert default.status_code == 200
    assert default.json()["totals"]["total"] == 1
    assert default.json()["totals"]["liked"] == 1
    assert "window" in default.json()

    # A wide explicit window is respected and counts both rows.
    assert wide.status_code == 200
    assert wide.json()["totals"]["total"] == 2


@pytest.mark.anyio
async def test_usage_requires_auth(configured_database: str) -> None:
    async with _client() as client:
        app_usage = await client.get("/app/usage")
        project_usage = await client.get(f"/app/projects/{uuid4()}/usage")
        api_usage = await client.get("/api/project/usage")

    assert app_usage.status_code == 401
    assert project_usage.status_code == 401
    assert api_usage.status_code == 401
    assert api_usage.json() == {"detail": "Unauthorized"}
