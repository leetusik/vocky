"""Transport-neutral accounts, tenancy, and credential service.

Owns the session lifecycle (open, commit/rollback) and translates SQLAlchemy
errors into domain errors. No HTTP surface, no password hashing (S2 owns
argon2), no token generation (callers pass pre-computed hashes).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vocky.accounts.repository import AccountsRepository
from vocky.accounts.types import (
    AuthTokenRecord,
    CreateAuthToken,
    CreateProject,
    CreateProjectCredential,
    CreateUser,
    ProjectCredentialRecord,
    ProjectRecord,
    TenantMemberRecord,
    TenantRecord,
    UserRecord,
)
from vocky.db import get_session_maker

# The project every fresh signup lands with, and the fallback an org-level key
# resolves to when a write names no project. There is deliberately **no**
# ``DEFAULT_ORG_NAME``: an org keeps its friendly auto-name
# (``"<localpart>'s workspace"``, minted in ``vocky.auth_api.signup``) because
# nothing ever resolves an org by name. The ``"default"`` that matters is the
# project.
DEFAULT_PROJECT_NAME = "default"


class AccountsPersistenceError(RuntimeError):
    """Raised when an accounts write cannot be persisted."""


class AccountsReadError(RuntimeError):
    """Raised when accounts data cannot be read from storage."""


class DuplicateEmailError(AccountsPersistenceError):
    """Raised when creating a user whose email is already registered.

    Lets the signup handler return a clean 409 rather than a generic 500.
    """


class AccountsService:
    """Application service for accounts, tenancy, project, and credential data."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    # -- users ------------------------------------------------------------

    async def create_user(self, payload: CreateUser) -> UserRecord:
        """Persist a user; raise ``DuplicateEmailError`` on a duplicate email."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                record = await repository.create_user(payload)
                await session.commit()
            except IntegrityError as exc:
                # ``users`` has a single unique constraint (uq_users_email), so
                # any integrity violation here is a duplicate email.
                await session.rollback()
                raise DuplicateEmailError(
                    "a user with this email already exists"
                ) from exc
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError("failed to persist user") from exc

        return record

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        """Return one user by email, or None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_user_by_email(email)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read user") from exc

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        """Return one user by id, or None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_user_by_id(user_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read user") from exc

    # -- tenancy ----------------------------------------------------------

    async def create_tenant_with_owner(
        self,
        user_id: UUID,
        name: str,
    ) -> tuple[TenantRecord, TenantMemberRecord]:
        """Create a tenant and its owner membership in one transaction.

        The signup primitive: inserts the tenant plus an ``owner`` row in
        ``tenant_members`` for ``user_id`` atomically, returning both records.
        """

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                tenant = await repository.create_tenant(name)
                member = await repository.add_tenant_member(
                    tenant_id=tenant.id,
                    user_id=user_id,
                    role="owner",
                )
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to create tenant with owner"
                ) from exc

        return tenant, member

    async def provision_signup(
        self,
        user_id: UUID,
        tenant_name: str,
    ) -> tuple[TenantRecord, TenantMemberRecord, ProjectRecord]:
        """Provision a new user's org + default project in one transaction.

        The signup primitive: inserts the tenant (org) named ``tenant_name``, an
        ``owner`` membership for ``user_id``, and the ``DEFAULT_PROJECT_NAME``
        project under that tenant — all atomically in one session — and returns
        the three records. Distinct from ``create_tenant_with_owner`` (which
        creates no project and is kept for callers that want a bare tenant): a
        fresh signup always lands with a project to capture into.

        The org name is passed in rather than defaulted: only the *project* has
        a canonical ``"default"`` name; the org keeps its friendly per-user
        auto-name.

        This narrows, but does not close, signup's orphan window — ``create_user``
        still commits in its own transaction before this one runs.
        """

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                tenant = await repository.create_tenant(tenant_name)
                member = await repository.add_tenant_member(
                    tenant_id=tenant.id,
                    user_id=user_id,
                    role="owner",
                )
                project = await repository.create_project(
                    CreateProject(tenant_id=tenant.id, name=DEFAULT_PROJECT_NAME)
                )
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to provision signup workspace"
                ) from exc

        return tenant, member, project

    async def get_tenant(self, tenant_id: UUID) -> TenantRecord | None:
        """Return one tenant by id, or None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_tenant(tenant_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read tenant") from exc

    async def list_tenants_for_user(self, user_id: UUID) -> tuple[TenantRecord, ...]:
        """Return the tenants a user is a member of, oldest-first."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.list_tenants_for_user(user_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read tenants") from exc

    # -- projects ---------------------------------------------------------

    async def create_project(self, payload: CreateProject) -> ProjectRecord:
        """Persist a project and return the stored record."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                record = await repository.create_project(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError("failed to persist project") from exc

        return record

    async def get_project(self, project_id: UUID) -> ProjectRecord | None:
        """Return one project by id, or None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_project(project_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read project") from exc

    async def list_projects_for_tenant(
        self,
        tenant_id: UUID,
    ) -> tuple[ProjectRecord, ...]:
        """Return a tenant's projects, oldest-first."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.list_projects_for_tenant(tenant_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read projects") from exc

    async def get_project_by_name(
        self,
        tenant_id: UUID,
        name: str,
    ) -> ProjectRecord | None:
        """Return a tenant's project by name (oldest-wins), or None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_project_by_name(tenant_id, name)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read project") from exc

    async def get_or_create_project(
        self,
        tenant_id: UUID,
        name: str,
    ) -> ProjectRecord:
        """Return the tenant's project named ``name``, creating it if absent.

        The idempotent project primitive, backing ``POST /app/projects``: read by
        name first, else insert. Race-safe against ``UNIQUE(tenant_id, name)`` —
        a concurrent insert that wins the race surfaces as an ``IntegrityError``
        on flush, which is rolled back and re-read so both callers converge on
        the same row (never a 500).
        """

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                existing = await repository.get_project_by_name(tenant_id, name)
                if existing is not None:
                    return existing
                try:
                    record = await repository.create_project(
                        CreateProject(tenant_id=tenant_id, name=name)
                    )
                    await session.commit()
                    return record
                except IntegrityError:
                    # A concurrent insert won the UNIQUE(tenant_id, name) race —
                    # roll back and re-read the row the other writer committed.
                    # This handler must stay nested *inside* the outer
                    # SQLAlchemyError block: IntegrityError is a SQLAlchemyError,
                    # so a sibling clause would never be reached.
                    await session.rollback()
                    raced = await repository.get_project_by_name(tenant_id, name)
                    if raced is not None:
                        return raced
                    # Nothing to converge on — a genuine integrity failure.
                    raise
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to get or create project"
                ) from exc

    # -- credentials ------------------------------------------------------

    async def create_project_credential(
        self,
        payload: CreateProjectCredential,
    ) -> ProjectCredentialRecord:
        """Persist a project credential and return its metadata record."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                record = await repository.create_project_credential(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to persist project credential"
                ) from exc

        return record

    async def list_project_credentials(
        self,
        project_id: UUID,
    ) -> tuple[ProjectCredentialRecord, ...]:
        """Return a project's credentials (active and revoked), oldest-first."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.list_project_credentials(project_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError(
                    "failed to read project credentials"
                ) from exc

    async def list_org_credentials(
        self,
        tenant_id: UUID,
    ) -> tuple[ProjectCredentialRecord, ...]:
        """Return a tenant's org-level (``project_id IS NULL``) credentials.

        Oldest-first, active and revoked, and disjoint from
        ``list_project_credentials``: an org key spans every project its tenant
        owns, so no per-project listing can surface it (P10).
        """

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.list_org_credentials(tenant_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read org credentials") from exc

    async def get_credential(
        self,
        credential_id: UUID,
    ) -> ProjectCredentialRecord | None:
        """Return one credential by id, or None when missing.

        Unscoped by design — one indexed read; the caller owns the ownership
        check and must answer 404 (never 403) when the record is outside its
        scope.
        """

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_credential(credential_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError(
                    "failed to read project credential"
                ) from exc

    async def get_active_credential_by_token_hash(
        self,
        token_hash: str,
    ) -> ProjectCredentialRecord | None:
        """Return the active credential for a token hash, or None."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_active_credential_by_token_hash(
                    token_hash
                )
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError(
                    "failed to read project credential"
                ) from exc

    async def revoke_credential(
        self,
        credential_id: UUID,
    ) -> ProjectCredentialRecord | None:
        """Soft-revoke a credential by id; None when missing."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                record = await repository.revoke_credential(credential_id)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to revoke project credential"
                ) from exc

        return record

    async def touch_credential_last_used(self, credential_id: UUID) -> None:
        """Stamp a credential's ``last_used_at`` to now."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                await repository.touch_credential_last_used(credential_id)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to update project credential"
                ) from exc

    # -- sessions ---------------------------------------------------------

    async def create_auth_token(self, payload: CreateAuthToken) -> AuthTokenRecord:
        """Persist a session token and return its metadata record."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                record = await repository.create_auth_token(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to persist auth token"
                ) from exc

        return record

    async def get_active_auth_token_by_hash(
        self,
        token_hash: str,
    ) -> AuthTokenRecord | None:
        """Return the active session token for a hash, or None."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                return await repository.get_active_auth_token_by_hash(token_hash)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsReadError("failed to read auth token") from exc

    async def delete_auth_token(self, token_hash: str) -> bool:
        """Delete a session token by hash (logout). True when a row was removed."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                deleted = await repository.delete_auth_token(token_hash)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to delete auth token"
                ) from exc

        return deleted

    async def touch_auth_token_last_used(self, token_hash: str) -> None:
        """Stamp a session token's ``last_used_at`` to now."""

        async with self._session_maker() as session:
            repository = AccountsRepository(session)
            try:
                await repository.touch_auth_token_last_used(token_hash)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise AccountsPersistenceError(
                    "failed to update auth token"
                ) from exc


def get_accounts_service() -> AccountsService:
    """Return the shared accounts service."""

    return AccountsService(get_session_maker())
