"""Persistence repository for accounts, tenancy, projects, and credentials.

The sole ORM boundary for the accounts domain: it maps ``Create*`` inputs to
models and models to ``*Record`` outputs, and never commits (the service owns
the transaction).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from vocky.persistence.models import (
    AuthTokenModel,
    ProjectCredentialModel,
    ProjectModel,
    TenantMemberModel,
    TenantModel,
    UserModel,
    utc_now,
)


class AccountsRepository:
    """Repository for accounts, tenancy, project, and credential persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- users ------------------------------------------------------------

    async def create_user(self, payload: CreateUser) -> UserRecord:
        """Persist a user and return the stored record."""

        model = UserModel(email=payload.email, password_hash=payload.password_hash)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_user_record(model)

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        """Return one user by email, or None when missing."""

        statement = select(UserModel).where(UserModel.email == email)
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_user_record(model) if model is not None else None

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        """Return one user by id, or None when missing."""

        model = await self._session.get(UserModel, user_id)
        return self._to_user_record(model) if model is not None else None

    # -- tenancy ----------------------------------------------------------

    async def create_tenant(self, name: str) -> TenantRecord:
        """Persist a tenant and return the stored record."""

        model = TenantModel(name=name)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_tenant_record(model)

    async def add_tenant_member(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        role: str,
    ) -> TenantMemberRecord:
        """Persist a tenant membership and return the stored record."""

        model = TenantMemberModel(tenant_id=tenant_id, user_id=user_id, role=role)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_tenant_member_record(model)

    async def get_tenant(self, tenant_id: UUID) -> TenantRecord | None:
        """Return one tenant by id, or None when missing."""

        model = await self._session.get(TenantModel, tenant_id)
        return self._to_tenant_record(model) if model is not None else None

    async def list_tenants_for_user(self, user_id: UUID) -> tuple[TenantRecord, ...]:
        """Return the tenants a user is a member of, oldest-first."""

        statement = (
            select(TenantModel)
            .join(TenantMemberModel, TenantMemberModel.tenant_id == TenantModel.id)
            .where(TenantMemberModel.user_id == user_id)
            .order_by(TenantModel.created_at, TenantModel.id)
        )
        models = (await self._session.execute(statement)).scalars().all()
        return tuple(self._to_tenant_record(model) for model in models)

    # -- projects ---------------------------------------------------------

    async def create_project(self, payload: CreateProject) -> ProjectRecord:
        """Persist a project and return the stored record."""

        model = ProjectModel(tenant_id=payload.tenant_id, name=payload.name)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_project_record(model)

    async def get_project(self, project_id: UUID) -> ProjectRecord | None:
        """Return one project by id, or None when missing."""

        model = await self._session.get(ProjectModel, project_id)
        return self._to_project_record(model) if model is not None else None

    async def list_projects_for_tenant(
        self,
        tenant_id: UUID,
    ) -> tuple[ProjectRecord, ...]:
        """Return a tenant's projects, oldest-first."""

        statement = (
            select(ProjectModel)
            .where(ProjectModel.tenant_id == tenant_id)
            .order_by(ProjectModel.created_at, ProjectModel.id)
        )
        models = (await self._session.execute(statement)).scalars().all()
        return tuple(self._to_project_record(model) for model in models)

    async def get_project_by_name(
        self,
        tenant_id: UUID,
        name: str,
    ) -> ProjectRecord | None:
        """Return a tenant's project by name, or None when missing.

        Oldest-wins by ``(created_at, id)`` — the same order
        ``list_projects_for_tenant`` uses, and the same order the org-level
        credentials migration's de-dupe picks its survivor by, so the migration
        and the runtime always agree on which row "the" project is. Backs
        ``get_or_create_project`` and the ``UNIQUE(tenant_id, name)`` constraint
        makes the match unique in practice.
        """

        statement = (
            select(ProjectModel)
            .where(
                ProjectModel.tenant_id == tenant_id,
                ProjectModel.name == name,
            )
            .order_by(ProjectModel.created_at, ProjectModel.id)
            .limit(1)
        )
        model = (await self._session.execute(statement)).scalars().first()
        return self._to_project_record(model) if model is not None else None

    # -- credentials ------------------------------------------------------

    async def create_project_credential(
        self,
        payload: CreateProjectCredential,
    ) -> ProjectCredentialRecord:
        """Persist an ingest credential and return its metadata record.

        ``payload.project_id`` may be ``None`` for an org-level credential; the
        row's ``tenant_id`` is always set and is what authorizes it.
        """

        model = ProjectCredentialModel(
            tenant_id=payload.tenant_id,
            project_id=payload.project_id,
            name=payload.name,
            token_prefix=payload.token_prefix,
            token_hash=payload.token_hash,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_credential_record(model)

    async def list_project_credentials(
        self,
        project_id: UUID,
    ) -> tuple[ProjectCredentialRecord, ...]:
        """Return a project's credentials (active and revoked), oldest-first."""

        statement = (
            select(ProjectCredentialModel)
            .where(ProjectCredentialModel.project_id == project_id)
            .order_by(ProjectCredentialModel.created_at, ProjectCredentialModel.id)
        )
        models = (await self._session.execute(statement)).scalars().all()
        return tuple(self._to_credential_record(model) for model in models)

    async def get_active_credential_by_token_hash(
        self,
        token_hash: str,
    ) -> ProjectCredentialRecord | None:
        """Return the active (non-revoked) credential for a token hash, or None."""

        statement = select(ProjectCredentialModel).where(
            ProjectCredentialModel.token_hash == token_hash,
            ProjectCredentialModel.revoked_at.is_(None),
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_credential_record(model) if model is not None else None

    async def revoke_credential(
        self,
        credential_id: UUID,
    ) -> ProjectCredentialRecord | None:
        """Soft-revoke a credential by id. Idempotent; None when missing."""

        model = await self._session.get(ProjectCredentialModel, credential_id)
        if model is None:
            return None
        if model.revoked_at is None:
            model.revoked_at = utc_now()
            await self._session.flush()
            await self._session.refresh(model)
        return self._to_credential_record(model)

    async def touch_credential_last_used(self, credential_id: UUID) -> None:
        """Stamp a credential's ``last_used_at`` to now."""

        statement = (
            update(ProjectCredentialModel)
            .where(ProjectCredentialModel.id == credential_id)
            .values(last_used_at=utc_now())
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(statement)

    # -- sessions ---------------------------------------------------------

    async def create_auth_token(self, payload: CreateAuthToken) -> AuthTokenRecord:
        """Persist a session token and return its metadata record."""

        model = AuthTokenModel(
            user_id=payload.user_id,
            token_hash=payload.token_hash,
            expires_at=payload.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_auth_token_record(model)

    async def get_active_auth_token_by_hash(
        self,
        token_hash: str,
    ) -> AuthTokenRecord | None:
        """Return the active (unexpired) session token for a hash, or None.

        A NULL ``expires_at`` means no expiry; otherwise the token is active only
        while ``expires_at`` is in the future.
        """

        now = utc_now()
        statement = select(AuthTokenModel).where(
            AuthTokenModel.token_hash == token_hash,
            (AuthTokenModel.expires_at.is_(None)) | (AuthTokenModel.expires_at > now),
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_auth_token_record(model) if model is not None else None

    async def delete_auth_token(self, token_hash: str) -> bool:
        """Delete a session token by hash (logout). True when a row was removed."""

        statement = (
            delete(AuthTokenModel)
            .where(AuthTokenModel.token_hash == token_hash)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(statement)
        return result.rowcount > 0

    async def touch_auth_token_last_used(self, token_hash: str) -> None:
        """Stamp a session token's ``last_used_at`` to now."""

        statement = (
            update(AuthTokenModel)
            .where(AuthTokenModel.token_hash == token_hash)
            .values(last_used_at=utc_now())
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(statement)

    # -- record mappers ---------------------------------------------------

    def _to_user_record(self, model: UserModel) -> UserRecord:
        return UserRecord(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            created_at=model.created_at,
        )

    def _to_tenant_record(self, model: TenantModel) -> TenantRecord:
        return TenantRecord(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
        )

    def _to_tenant_member_record(
        self,
        model: TenantMemberModel,
    ) -> TenantMemberRecord:
        return TenantMemberRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            role=model.role,
            created_at=model.created_at,
        )

    def _to_project_record(self, model: ProjectModel) -> ProjectRecord:
        return ProjectRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            created_at=model.created_at,
        )

    def _to_credential_record(
        self,
        model: ProjectCredentialModel,
    ) -> ProjectCredentialRecord:
        return ProjectCredentialRecord(
            id=model.id,
            tenant_id=model.tenant_id,
            project_id=model.project_id,
            name=model.name,
            token_prefix=model.token_prefix,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            revoked_at=model.revoked_at,
        )

    def _to_auth_token_record(self, model: AuthTokenModel) -> AuthTokenRecord:
        return AuthTokenRecord(
            id=model.id,
            user_id=model.user_id,
            created_at=model.created_at,
            expires_at=model.expires_at,
            last_used_at=model.last_used_at,
        )
