"""Org-level (``project_id IS NULL``) credential scoping — the P10.S2 dark path.

Nothing in production mints an org-level credential yet (P10.S3 adds the mint
surface), so these tests construct one **directly at the service layer**. That is
not a breach of S1's "no NULL rows" invariant — that invariant is about
production code paths, and this branch is exactly what needs proving before it
can be turned on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

import vocky.api as api_module
from vocky.accounts import (
    CreateProject,
    CreateProjectCredential,
    CreateUser,
    ProjectCredentialRecord,
    get_accounts_service,
)
from vocky.accounts.security import generate_opaque_token, hash_password, sha256_hex
from vocky.api import routes as api_routes
from vocky.app_api import serialize_credential
from vocky.auth import ProjectCredentialAuthMiddleware
from vocky.capture_queue import CaptureQueue
from vocky.db import get_engine
from vocky.project_feedback_api import routes as project_feedback_routes
from vocky.usage_api import routes as usage_routes


def _client(routes: list, key: str) -> httpx.AsyncClient:
    """Return an ASGI client presenting ``key`` as the ingest Bearer token."""

    app = Starlette(routes=routes)
    app.add_middleware(ProjectCredentialAuthMiddleware)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {key}"},
    )


async def _mint_credential(tenant_id: UUID, project_id: UUID | None) -> str:
    """Mint a credential at org scope (``project_id=None``) or project scope."""

    key = f"vk_{generate_opaque_token()}"
    await get_accounts_service().create_project_credential(
        CreateProjectCredential(
            tenant_id=tenant_id,
            project_id=project_id,
            token_prefix=key[:12],
            token_hash=sha256_hex(key),
            name="org key" if project_id is None else "project key",
        )
    )
    return key


async def _seed_other_tenant_project() -> UUID:
    """Create an unrelated tenant with one project; return that project's id."""

    service = get_accounts_service()
    user = await service.create_user(
        CreateUser(
            email=f"other-{uuid4()}@example.com",
            password_hash=hash_password("test-password-123"),
        )
    )
    tenant, _member = await service.create_tenant_with_owner(user.id, "other org")
    project = await service.create_project(
        CreateProject(tenant_id=tenant.id, name="other project")
    )
    return project.id


async def _seed_feedback(feedback_id: str, project_id: UUID, ingested_at: datetime) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events "
                "(id, message, source_product, ingested_at, project_id) VALUES "
                "(:id, 'row', 'changple5', :ingested_at, :project_id)"
            ),
            {
                "id": feedback_id,
                "ingested_at": ingested_at,
                "project_id": str(project_id),
            },
        )


@pytest.mark.anyio
async def test_org_key_captures_into_named_project_then_default(
    monkeypatch: pytest.MonkeyPatch,
    configured_project_credential,
) -> None:
    """An org key get-or-creates the named project, and falls back to ``default``."""

    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    tenant_id = configured_project_credential.tenant_id
    org_key = await _mint_credential(tenant_id, None)
    service = get_accounts_service()
    assert await service.get_project_by_name(tenant_id, "mobile") is None

    async with _client(api_routes, org_key) as client:
        named = await client.post(
            "/api/feedback",
            json={"message": "named", "source": {"product": "p"}, "project": "mobile"},
        )
        omitted = await client.post(
            "/api/feedback",
            json={"message": "omitted", "source": {"product": "p"}},
        )

    assert (named.status_code, omitted.status_code) == (202, 202)

    mobile = await service.get_project_by_name(tenant_id, "mobile")
    default = await service.get_project_by_name(tenant_id, "default")
    assert mobile is not None and default is not None

    first = await queue.pop_job(timeout_seconds=1)
    second = await queue.pop_job(timeout_seconds=1)
    assert first is not None and second is not None
    assert first.payload.project_id == mobile.id
    assert second.payload.project_id == default.id

    await redis_client.aclose()


@pytest.mark.anyio
async def test_project_bound_key_ignores_the_project_field(
    monkeypatch: pytest.MonkeyPatch,
    configured_project_credential,
) -> None:
    """A project-bound key is byte-for-byte unchanged: ``project`` is ignored."""

    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    async with _client(api_routes, configured_project_credential.key) as client:
        response = await client.post(
            "/api/feedback",
            json={"message": "bound", "source": {"product": "p"}, "project": "mobile"},
        )

    # Honored would land elsewhere; rejected would 400. Neither: it is ignored.
    assert response.status_code == 202
    job = await queue.pop_job(timeout_seconds=1)
    assert job is not None
    assert job.payload.project_id == configured_project_credential.project_id
    assert (
        await get_accounts_service().get_project_by_name(
            configured_project_credential.tenant_id, "mobile"
        )
        is None
    )

    await redis_client.aclose()


@pytest.mark.anyio
async def test_org_key_reads_its_whole_org_and_never_another_tenant(
    configured_project_credential,
) -> None:
    """An org key spans every project it owns; other tenants stay 404-invisible."""

    tenant_id = configured_project_credential.tenant_id
    second = await get_accounts_service().create_project(
        CreateProject(tenant_id=tenant_id, name="second project")
    )
    outside_project = await _seed_other_tenant_project()

    mine_a = "00000000-0000-0000-0000-0000000000b1"
    mine_b = "00000000-0000-0000-0000-0000000000b2"
    outside = "00000000-0000-0000-0000-0000000000b3"
    await _seed_feedback(
        mine_a, configured_project_credential.project_id, datetime(2026, 6, 1, 10, tzinfo=UTC)
    )
    await _seed_feedback(mine_b, second.id, datetime(2026, 6, 1, 11, tzinfo=UTC))
    await _seed_feedback(outside, outside_project, datetime(2026, 6, 1, 12, tzinfo=UTC))

    org_key = await _mint_credential(tenant_id, None)
    async with _client(project_feedback_routes, org_key) as client:
        listed = await client.get("/api/project/feedback")
        cross = await client.get(f"/api/project/feedback/{outside}")

    assert listed.status_code == 200
    records = listed.json()["records"]
    assert [record["id"] for record in records] == [mine_b, mine_a]
    # The org key spans many projects, so each record must name its own.
    assert records[0]["project_id"] == str(second.id)
    # 404, never 403: a cross-tenant id is indistinguishable from a missing one.
    assert cross.status_code == 404
    assert cross.json() == {"detail": "feedback not found"}


@pytest.mark.anyio
async def test_org_key_usage_aggregates_project_credentials(
    configured_project_credential,
) -> None:
    """``/api/project/usage`` under an org key aggregates across its projects."""

    tenant_id = configured_project_credential.tenant_id
    second = await get_accounts_service().create_project(
        CreateProject(tenant_id=tenant_id, name="second project")
    )
    await _mint_credential(tenant_id, second.id)
    org_key = await _mint_credential(tenant_id, None)

    async with _client(usage_routes, org_key) as client:
        response = await client.get("/api/project/usage")

    assert response.status_code == 200
    project_ids = {entry["project_id"] for entry in response.json()["credentials"]}
    assert project_ids == {
        str(configured_project_credential.project_id),
        str(second.id),
    }
    # KNOWN GAP, handed to P10.S3: a per-project listing cannot return
    # ``project_id IS NULL`` rows, so the org key omits itself here. S3 must
    # union ``list_org_credentials`` in.
    assert None not in project_ids


def test_serialize_credential_renders_null_for_an_org_row() -> None:
    """An org row serializes ``project_id: null``, not the string ``"None"``."""

    payload = serialize_credential(
        ProjectCredentialRecord(
            id=uuid4(),
            tenant_id=uuid4(),
            project_id=None,
            name="org key",
            token_prefix="vk_abc",
            created_at=datetime(2026, 6, 1, tzinfo=UTC),
            last_used_at=None,
            revoked_at=None,
        )
    )

    assert payload["project_id"] is None
