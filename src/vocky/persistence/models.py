"""ORM models for persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from vocky.persistence.base import Base


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class FeedbackEventModel(Base):
    """Stored feedback event."""

    __tablename__ = "feedback_events"
    __table_args__ = (
        Index("ix_feedback_events_ingested_at", "ingested_at"),
        Index("ix_feedback_events_event_at", "event_at"),
        Index("ix_feedback_events_source_product", "source_product"),
        Index("ix_feedback_events_feedback_value", "feedback_value"),
        Index("ix_feedback_events_channel", "channel"),
        Index("ix_feedback_events_conversation_id", "conversation_id"),
        Index("ix_feedback_events_session_id", "session_id"),
        Index("ix_feedback_events_user_id", "user_id"),
        Index("ix_feedback_events_trigger_type", "trigger_type"),
        Index("ix_feedback_events_recorded_by", "recorded_by"),
        Index("ix_feedback_events_target_type", "target_type"),
        Index("ix_feedback_events_tags_gin", "tags", postgresql_using="gin"),
        Index("ix_feedback_events_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_product: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_value: Mapped[int | None] = mapped_column(nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_integration: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Capture-time provenance marker: ``agent`` | ``human`` | NULL (unspecified).
    #: Never backfilled and never inferred; validated in ``vocky.recorded_by``.
    recorded_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    messages: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    used_context: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class FeedbackCommentModel(Base):
    """Operator-authored comment attached to a stored feedback event."""

    __tablename__ = "feedback_comments"
    __table_args__ = (
        Index("ix_feedback_comments_feedback_id", "feedback_id"),
        Index("ix_feedback_comments_feedback_id_created_at", "feedback_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    feedback_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feedback_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class FeedbackAttachmentModel(Base):
    """Image attachment uploaded for a feedback event.

    ``feedback_id`` is nullable because attachments are uploaded synchronously
    before the async capture path persists the feedback row; the worker links
    them after persist. ``claimed_user_id`` / ``claimed_source_product`` record
    the scope asserted at upload so the worker links only to a matching feedback
    event and one product cannot attach another user's image.
    """

    __tablename__ = "feedback_attachments"
    __table_args__ = (
        Index("ix_feedback_attachments_feedback_id", "feedback_id"),
        Index(
            "ix_feedback_attachments_feedback_id_created_at",
            "feedback_id",
            "created_at",
        ),
        Index("ix_feedback_attachments_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    feedback_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feedback_events.id", ondelete="CASCADE"),
        nullable=True,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_source_product: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UserModel(Base):
    """Registered account user (email + argon2id password hash)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TenantModel(Base):
    """Tenant (workspace). Ownership lives in ``tenant_members``, not here."""

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TenantMemberModel(Base):
    """Membership linking a user to a tenant with a role."""

    __tablename__ = "tenant_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id"),
        Index("ix_tenant_members_tenant_id", "tenant_id"),
        Index("ix_tenant_members_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ProjectModel(Base):
    """Project owned by a tenant."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name"),
        Index("ix_projects_tenant_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ProjectCredentialModel(Base):
    """API ingest credential. Only the sha256 ``token_hash`` is stored.

    ``tenant_id`` is **always** set and is what authorizes the key at org scope.
    ``project_id`` narrows it: when set, the key is bound to that one project
    (and dies with it, via the CASCADE FK); ``project_id IS NULL`` means the
    credential is **org-level** and spans every project in ``tenant_id``.
    """

    __tablename__ = "project_credentials"
    __table_args__ = (
        Index("ix_project_credentials_project_id", "project_id"),
        Index("ix_project_credentials_tenant_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AuthTokenModel(Base):
    """Opaque DB-backed session token for a user. Only the sha256 hash is stored."""

    __tablename__ = "auth_tokens"
    __table_args__ = (Index("ix_auth_tokens_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
