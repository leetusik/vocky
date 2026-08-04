"""Shared pytest fixtures for Vocky."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from typing import NamedTuple
from uuid import UUID, uuid4

import psycopg
import pytest
import pytest_asyncio
from alembic.config import Config
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from alembic import command
from vocky.accounts import (
    CreateProject,
    CreateProjectCredential,
    CreateUser,
    get_accounts_service,
)
from vocky.accounts.security import generate_opaque_token, hash_password, sha256_hex
from vocky.config import get_settings
from vocky.db import dispose_engine, get_engine
from vocky.rate_limit import reset_rate_limits

DEFAULT_DATABASE_URL = "postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky"


@pytest.fixture(autouse=True)
def _isolated_rate_limits() -> Generator[None, None, None]:
    """Reset the in-process auth rate limiter before every test.

    `httpx.ASGITransport` gives every test client the same fixed peer address,
    so without this every test in the session would share one rate-limit
    bucket per route.
    """

    reset_rate_limits()
    yield
    reset_rate_limits()


class SeededCredential(NamedTuple):
    """A seeded user -> tenant -> project -> active credential for /api/* tests.

    ``key`` is the plaintext ``vk_`` ingest key (valid Bearer for ``/api/*``);
    the other ids let cross-tenant / scoping tests reference the seeded records.
    """

    key: str
    project_id: UUID
    tenant_id: UUID
    user_id: UUID
    credential_id: UUID


def set_database_url(database_url: str) -> None:
    """Update the active DATABASE_URL and clear cached settings."""

    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()


def render_url(url: URL) -> str:
    """Render a SQLAlchemy URL with its password preserved."""

    return url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def base_database_url() -> str:
    """Return the base database URL used for tests."""

    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Run anyio-backed tests on asyncio."""

    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url(base_database_url: str) -> Generator[str, None, None]:
    """Reset and migrate a dedicated PostgreSQL database used for tests."""

    original_database_url = os.environ.get("DATABASE_URL")
    base_url = make_url(base_database_url)
    configured_test_database_url = os.getenv("TEST_DATABASE_URL")
    if configured_test_database_url is None:
        test_database_name = f"{base_url.database or 'vocky'}_test"
        test_url = base_url.set(database=test_database_name)
    else:
        test_url = make_url(configured_test_database_url)

    if render_url(base_url) == render_url(test_url):
        raise RuntimeError("TEST_DATABASE_URL must not point to the same database as DATABASE_URL")

    base_sync_database_url = render_url(base_url.set(drivername="postgresql"))
    test_sync_database_url = render_url(test_url.set(drivername="postgresql"))

    with psycopg.connect(base_sync_database_url, autocommit=True) as connection:
        test_database_name = test_url.database
        if test_database_name is None:
            raise RuntimeError("TEST_DATABASE_URL must include a database name")

        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (test_database_name,),
        ).fetchone()
        if exists is None:
            try:
                connection.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database_name))
                )
            except psycopg.Error as exc:  # pragma: no cover
                raise RuntimeError(
                    "Unable to create the test database automatically. "
                    "Set TEST_DATABASE_URL to an existing disposable database."
                ) from exc

    with psycopg.connect(test_sync_database_url, autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute("GRANT ALL ON SCHEMA public TO CURRENT_USER")

    set_database_url(render_url(test_url))
    command.upgrade(Config("alembic.ini"), "head")

    try:
        yield render_url(test_url)
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


@pytest_asyncio.fixture
async def configured_database(test_database_url: str) -> str:
    """Point the app at the test database and clear state between tests."""

    set_database_url(test_database_url)
    await dispose_engine()

    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE feedback_events, feedback_comments, "
                "feedback_attachments, users, tenants, tenant_members, "
                "projects, project_credentials, auth_tokens CASCADE"
            )
        )

    yield test_database_url

    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE feedback_events, feedback_comments, "
                "feedback_attachments, users, tenants, tenant_members, "
                "projects, project_credentials, auth_tokens CASCADE"
            )
        )

    await dispose_engine()


@pytest_asyncio.fixture
async def configured_project_credential(
    configured_database: str,
) -> SeededCredential:
    """Seed a user, tenant, project, and active credential; return the raw key.

    The plaintext ``vk_`` key it returns is a valid Bearer credential for the
    ``/api/*`` ingest middleware; ``/api/*`` tests attach it to authenticate.
    """

    service = get_accounts_service()
    user = await service.create_user(
        CreateUser(
            email=f"api-cred-{uuid4()}@example.com",
            password_hash=hash_password("test-password-123"),
        )
    )
    tenant, _member = await service.create_tenant_with_owner(user.id, "ingest workspace")
    project = await service.create_project(
        CreateProject(tenant_id=tenant.id, name="ingest project")
    )
    key = f"vk_{generate_opaque_token()}"
    credential = await service.create_project_credential(
        CreateProjectCredential(
            tenant_id=tenant.id,
            project_id=project.id,
            token_prefix=key[:12],
            token_hash=sha256_hex(key),
            name="test ingest key",
        )
    )
    return SeededCredential(
        key=key,
        project_id=project.id,
        tenant_id=tenant.id,
        user_id=user.id,
        credential_id=credential.id,
    )
