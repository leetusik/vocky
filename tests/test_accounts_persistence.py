"""Persistence tests for the accounts/tenancy store."""

from __future__ import annotations

import pytest

from vocky.accounts import (
    AccountsService,
    CreateAuthToken,
    CreateProject,
    CreateProjectCredential,
    CreateUser,
    DuplicateEmailError,
    get_accounts_service,
)
from vocky.db import get_session_maker


def _service() -> AccountsService:
    return AccountsService(get_session_maker())


@pytest.mark.asyncio
async def test_create_user_and_fetch_by_email_and_id(configured_database: str) -> None:
    service = _service()

    created = await service.create_user(
        CreateUser(email="owner@example.com", password_hash="argon2-hash")
    )

    by_email = await service.get_user_by_email("owner@example.com")
    by_id = await service.get_user_by_id(created.id)

    assert by_email is not None and by_email.id == created.id
    assert by_id is not None and by_id.email == "owner@example.com"
    assert by_id.password_hash == "argon2-hash"
    assert await service.get_user_by_email("missing@example.com") is None


@pytest.mark.asyncio
async def test_duplicate_email_raises(configured_database: str) -> None:
    service = _service()
    await service.create_user(CreateUser(email="dup@example.com", password_hash="h"))

    with pytest.raises(DuplicateEmailError):
        await service.create_user(CreateUser(email="dup@example.com", password_hash="h2"))


@pytest.mark.asyncio
async def test_create_tenant_with_owner_yields_owner_membership(
    configured_database: str,
) -> None:
    service = _service()
    user = await service.create_user(
        CreateUser(email="founder@example.com", password_hash="h")
    )

    tenant, member = await service.create_tenant_with_owner(user.id, "Acme")

    assert member.role == "owner"
    assert member.tenant_id == tenant.id and member.user_id == user.id
    tenants = await service.list_tenants_for_user(user.id)
    assert [t.id for t in tenants] == [tenant.id]


@pytest.mark.asyncio
async def test_project_under_tenant(configured_database: str) -> None:
    service = _service()
    user = await service.create_user(
        CreateUser(email="proj@example.com", password_hash="h")
    )
    tenant, _ = await service.create_tenant_with_owner(user.id, "Workspace")

    project = await service.create_project(
        CreateProject(tenant_id=tenant.id, name="Website")
    )

    assert project.tenant_id == tenant.id
    listed = await service.list_projects_for_tenant(tenant.id)
    assert [p.id for p in listed] == [project.id]
    assert (await service.get_project(project.id)).name == "Website"


@pytest.mark.asyncio
async def test_credential_lifecycle_active_lookup_and_revoke(
    configured_database: str,
) -> None:
    service = _service()
    user = await service.create_user(
        CreateUser(email="cred@example.com", password_hash="h")
    )
    tenant, _ = await service.create_tenant_with_owner(user.id, "Tenant")
    project = await service.create_project(
        CreateProject(tenant_id=tenant.id, name="P")
    )

    credential = await service.create_project_credential(
        CreateProjectCredential(
            tenant_id=tenant.id,
            project_id=project.id,
            token_prefix="vk_ab12",
            token_hash="hash-abc",
            name="ci",
        )
    )

    active = await service.get_active_credential_by_token_hash("hash-abc")
    assert active is not None and active.id == credential.id
    assert not hasattr(active, "token_hash")  # metadata only

    revoked = await service.revoke_credential(credential.id)
    assert revoked is not None and revoked.revoked_at is not None
    assert await service.get_active_credential_by_token_hash("hash-abc") is None
    # revoked credential still listed for the project
    listed = await service.list_project_credentials(project.id)
    assert [c.id for c in listed] == [credential.id]


@pytest.mark.asyncio
async def test_auth_token_create_lookup_and_delete(configured_database: str) -> None:
    service = _service()
    user = await service.create_user(
        CreateUser(email="session@example.com", password_hash="h")
    )

    token = await service.create_auth_token(
        CreateAuthToken(user_id=user.id, token_hash="sess-hash")
    )

    found = await service.get_active_auth_token_by_hash("sess-hash")
    assert found is not None and found.id == token.id and found.user_id == user.id

    assert await service.delete_auth_token("sess-hash") is True
    assert await service.get_active_auth_token_by_hash("sess-hash") is None
    assert await service.delete_auth_token("sess-hash") is False


def test_factory_returns_service() -> None:
    assert isinstance(get_accounts_service(), AccountsService)
