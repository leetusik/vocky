"""P10.S1: signup provisioning, get-or-create projects, and the org-key schema.

Covers the four things the schema slice makes true: signup lands a ``"default"``
project under a *friendly*-named org, project creation is idempotent on name,
every minted credential carries ``tenant_id``, and the migration round-trips
(including its de-dupe branch, which a clean database never exercises).
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from starlette.applications import Starlette

import vocky.accounts.service as accounts_service
from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.app_api import routes as app_api_routes
from vocky.auth_api import routes as auth_routes
from vocky.db import dispose_engine, get_engine

_TRUNCATE = (
    "TRUNCATE TABLE feedback_events, feedback_comments, feedback_attachments, "
    "users, tenants, tenant_members, projects, project_credentials, "
    "auth_tokens CASCADE"
)


def _client() -> httpx.AsyncClient:
    app = Starlette(
        routes=[*auth_routes, *app_api_routes],
        exception_handlers={AuthError: auth_error_handler},
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def _signup(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/auth/signup", json={"email": email, "password": "hunter2pass"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.mark.anyio
async def test_signup_provisions_default_project_under_friendly_org(
    configured_database: str,
) -> None:
    """Decision 3, pinned: only the *project* is named "default"."""

    async with _client() as client:
        signup = await client.post(
            "/auth/signup", json={"email": "alice@example.com", "password": "hunter2pass"}
        )
        headers = {"Authorization": f"Bearer {signup.json()['token']}"}
        listed = await client.get("/app/projects", headers=headers)

    body = signup.json()
    # The org keeps its friendly auto-name — there is deliberately no
    # DEFAULT_ORG_NAME, so a later slice cannot quietly adopt a "default" org.
    assert body["tenant"]["name"] == "alice's workspace"
    assert not hasattr(accounts_service, "DEFAULT_ORG_NAME")
    assert accounts_service.DEFAULT_PROJECT_NAME == "default"

    assert body["project"]["name"] == "default"
    assert [p["name"] for p in listed.json()["projects"]] == ["default"]
    assert [p["id"] for p in listed.json()["projects"]] == [body["project"]["id"]]


@pytest.mark.anyio
async def test_project_creation_is_idempotent_on_name(
    configured_database: str,
) -> None:
    """Both the service primitive and ``POST /app/projects`` converge on one row."""

    async with _client() as client:
        headers = await _signup(client, "bob@example.com")
        first = await client.post("/app/projects", json={"name": "Website"}, headers=headers)
        second = await client.post("/app/projects", json={"name": "Website"}, headers=headers)
        listed = await client.get("/app/projects", headers=headers)

    # The duplicate name is a 201 returning the existing row, never a 500.
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["project"]["id"] == second.json()["project"]["id"]
    assert [p["name"] for p in listed.json()["projects"]] == ["default", "Website"]

    service = accounts_service.get_accounts_service()
    tenant_id = UUID(first.json()["project"]["tenant_id"])
    again = await service.get_or_create_project(tenant_id, "Website")
    assert str(again.id) == first.json()["project"]["id"]


@pytest.mark.anyio
async def test_minted_credential_carries_tenant_id(configured_database: str) -> None:
    """``tenant_id`` is always stored, though the API never exposes it."""

    async with _client() as client:
        headers = await _signup(client, "carol@example.com")
        project = (await client.get("/app/projects", headers=headers)).json()["projects"][0]
        created = await client.post(
            f"/app/projects/{project['id']}/credentials", headers=headers
        )

    assert created.status_code == 201
    credential_id = created.json()["credential"]["id"]
    assert "tenant_id" not in created.json()["credential"]

    async with get_engine().begin() as connection:
        row = (
            await connection.execute(
                text(
                    "SELECT tenant_id, project_id FROM project_credentials "
                    "WHERE id = :id"
                ),
                {"id": credential_id},
            )
        ).one()

    assert str(row.tenant_id) == project["tenant_id"]
    # S1 mints no org-level rows: project_id is still bound.
    assert str(row.project_id) == project["id"]


def test_org_credentials_migration_round_trip(test_database_url: str) -> None:
    """Downgrade, seed duplicates + children, upgrade: one survivor, kids repointed.

    Sync on purpose — alembic's ``env.py`` calls ``asyncio.run``, so this cannot
    run inside the anyio loop. ``dispose_engine()`` first (conftest's pattern) so
    the async pool holds no connection while DDL runs. Ends back at head, so it
    is self-restoring for the rest of the session.
    """

    asyncio.run(dispose_engine())
    sync_url = (
        make_url(test_database_url)
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )
    config = Config("alembic.ini")

    with psycopg.connect(sync_url, autocommit=True) as connection:
        connection.execute(_TRUNCATE)

    # Target the revision *before* org credentials (``20260728_1200``) by name
    # rather than by ``"-1"``: this test exercises that one migration, so a
    # relative step silently retargets itself onto whatever the current head is
    # (P14 added ``20260805_1200`` on top). Everything above it is downgraded
    # too, and the closing ``upgrade("head")`` puts the whole chain back.
    command.downgrade(config, "20260716_1600")

    tenant_id, survivor_id, dead_id = uuid4(), uuid4(), uuid4()
    credential_id, feedback_id = uuid4(), uuid4()
    with psycopg.connect(sync_url, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO tenants (id, name) VALUES (%s, 'dupes')", (tenant_id,)
        )
        # Same (tenant_id, name); the older row must win.
        connection.execute(
            "INSERT INTO projects (id, tenant_id, name, created_at) VALUES "
            "(%s, %s, 'dup', '2026-01-01T00:00:00Z'), "
            "(%s, %s, 'dup', '2026-02-01T00:00:00Z')",
            (survivor_id, tenant_id, dead_id, tenant_id),
        )
        # Children hanging off the row that is about to be deleted.
        connection.execute(
            "INSERT INTO project_credentials (id, project_id, token_prefix, token_hash) "
            "VALUES (%s, %s, 'vk_dead', 'hash-dead')",
            (credential_id, dead_id),
        )
        connection.execute(
            "INSERT INTO feedback_events "
            "(id, message, source_product, ingested_at, project_id) "
            "VALUES (%s, 'row', 'changple5', now(), %s)",
            (feedback_id, dead_id),
        )

    command.upgrade(config, "head")

    with psycopg.connect(sync_url, autocommit=True) as connection:
        projects = connection.execute(
            "SELECT id FROM projects WHERE tenant_id = %s", (tenant_id,)
        ).fetchall()
        credential = connection.execute(
            "SELECT project_id, tenant_id FROM project_credentials WHERE id = %s",
            (credential_id,),
        ).fetchone()
        feedback = connection.execute(
            "SELECT project_id FROM feedback_events WHERE id = %s", (feedback_id,)
        ).fetchone()

        # The de-dupe merged onto the oldest row and repointed both child tables.
        assert projects == [(survivor_id,)]
        assert credential == (survivor_id, tenant_id)
        assert feedback == (survivor_id,)

        # UNIQUE(tenant_id, name) now rejects a re-insert of the merged name.
        with pytest.raises(psycopg.errors.UniqueViolation):
            connection.execute(
                "INSERT INTO projects (id, tenant_id, name) VALUES (%s, %s, 'dup')",
                (uuid4(), tenant_id),
            )

        connection.execute(_TRUNCATE)
