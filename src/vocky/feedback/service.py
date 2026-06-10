"""Transport-neutral feedback service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID

from vocky.db import get_session_maker
from vocky.feedback.repository import FeedbackRepository
from vocky.feedback.types import (
    CreateFeedbackAttachment,
    CreateFeedbackComment,
    CreateFeedbackEvent,
    FeedbackAttachmentRecord,
    FeedbackCommentRecord,
    FeedbackEventRecord,
    FeedbackListPage,
    FeedbackMetrics,
    FeedbackMetricsQuery,
    FeedbackSummary,
    ListFeedbackQuery,
    SummarizeFeedbackQuery,
)


class FeedbackPersistenceError(RuntimeError):
    """Raised when a feedback write cannot be persisted."""


class FeedbackReadError(RuntimeError):
    """Raised when feedback cannot be read from storage."""


class FeedbackService:
    """Application service for feedback persistence and reads."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def create_feedback_event(
        self,
        payload: CreateFeedbackEvent,
    ) -> FeedbackEventRecord:
        """Persist a feedback event and return the stored record."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                record = await repository.create_feedback_event(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback event"
                ) from exc

        return record

    async def create_feedback_event_with_attachments(
        self,
        payload: CreateFeedbackEvent,
    ) -> FeedbackEventRecord:
        """Persist a feedback event and link its claimed attachments in one txn.

        The event insert and the guarded attachment link share one session and
        one commit. Linking is scope-verified against the event's
        ``(user_id, source_product)`` and never fails the write: misrouted,
        missing, or already-linked attachments are skipped and logged.
        """

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                record = await repository.create_feedback_event(payload)
                if payload.attachment_ids:
                    await repository.link_attachments_to_feedback(
                        record.id,
                        payload.attachment_ids,
                        user_id=payload.user_id,
                        source_product=payload.source_product,
                    )
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback event"
                ) from exc

        return record

    async def list_feedback(
        self,
        query: ListFeedbackQuery,
    ) -> FeedbackListPage:
        """Return a cursor-paginated list of feedback records."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.list_feedback(query)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc

    async def list_feedback_with_comments(
        self,
        query: ListFeedbackQuery,
    ) -> tuple[FeedbackListPage, dict[UUID, tuple[FeedbackCommentRecord, ...]]]:
        """Return a page of feedback records plus their operator comments.

        The page and its comments are read in a single session, and comments are
        fetched in one batched query keyed by feedback id to avoid N+1 lookups.
        """

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                page = await repository.list_feedback(query)
                comments_by_id = await repository.list_comments_for_feedback_ids(
                    [record.id for record in page.records]
                )
                return page, comments_by_id
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc

    async def get_feedback_event(self, feedback_id: UUID) -> FeedbackEventRecord | None:
        """Return one feedback record by ID."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.get_feedback_event(feedback_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc

    async def update_feedback_event(
        self,
        feedback_id: UUID,
        updates: Mapping[str, Any],
    ) -> FeedbackEventRecord | None:
        """Update one feedback record by ID."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                record = await repository.update_feedback_event(feedback_id, updates)
                await session.commit()
                return record
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback event"
                ) from exc

    async def delete_feedback_event(
        self, feedback_id: UUID
    ) -> tuple[bool, tuple[str, ...]]:
        """Delete one feedback record and return its attachment storage keys.

        The storage keys are gathered before the cascade removes the attachment
        rows, in the same transaction, so the caller can delete the files after
        the DB commit. Returns ``(deleted, storage_keys)``; ``storage_keys`` is
        empty when the record was not found.
        """

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                storage_keys = await repository.list_storage_keys_for_feedback(
                    feedback_id
                )
                deleted = await repository.delete_feedback_event(feedback_id)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback event"
                ) from exc

        return (deleted, storage_keys if deleted else ())

    async def create_feedback_comment(
        self,
        payload: CreateFeedbackComment,
    ) -> FeedbackCommentRecord:
        """Persist an operator comment and return the stored record."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                record = await repository.create_feedback_comment(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback comment"
                ) from exc

        return record

    async def list_feedback_comments(
        self,
        feedback_id: UUID,
    ) -> tuple[FeedbackCommentRecord, ...]:
        """Return one feedback event's operator comments, oldest-first."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.list_feedback_comments(feedback_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback comments") from exc

    async def create_unlinked_attachment(
        self,
        payload: CreateFeedbackAttachment,
    ) -> FeedbackAttachmentRecord:
        """Persist an uploaded, not-yet-linked attachment and return it."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                record = await repository.create_feedback_attachment(payload)
                await session.commit()
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback attachment"
                ) from exc

        return record

    async def get_feedback_attachment(
        self,
        attachment_id: UUID,
    ) -> FeedbackAttachmentRecord | None:
        """Return one stored attachment by id, or None when missing."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.get_feedback_attachment(attachment_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback attachment") from exc

    async def list_feedback_attachments(
        self,
        feedback_id: UUID,
    ) -> tuple[FeedbackAttachmentRecord, ...]:
        """Return one feedback event's attachments, oldest-first."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.list_feedback_attachments(feedback_id)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError(
                    "failed to read feedback attachments"
                ) from exc

    async def list_feedback_with_comments_and_attachments(
        self,
        query: ListFeedbackQuery,
    ) -> tuple[
        FeedbackListPage,
        dict[UUID, tuple[FeedbackCommentRecord, ...]],
        dict[UUID, tuple[FeedbackAttachmentRecord, ...]],
    ]:
        """Return a page of feedback plus its comments and attachments.

        All reads share one session; comments and attachments are each fetched
        in one batched query keyed by feedback id to avoid N+1 lookups.
        """

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                page = await repository.list_feedback(query)
                ids = [record.id for record in page.records]
                comments_by_id = await repository.list_comments_for_feedback_ids(ids)
                attachments_by_id = await repository.list_attachments_for_feedback_ids(
                    ids
                )
                return page, comments_by_id, attachments_by_id
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc

    async def get_user_attachment(
        self,
        *,
        feedback_id: UUID,
        attachment_id: UUID,
        user_id: str,
        source_product: str,
    ) -> FeedbackAttachmentRecord | None:
        """Return an attachment for an end-user download, scope-checked."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.get_user_attachment(
                    feedback_id=feedback_id,
                    attachment_id=attachment_id,
                    user_id=user_id,
                    source_product=source_product,
                )
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError(
                    "failed to read feedback attachment"
                ) from exc

    async def get_admin_attachment(
        self,
        *,
        feedback_id: UUID,
        attachment_id: UUID,
    ) -> FeedbackAttachmentRecord | None:
        """Return an attachment for an operator download by feedback linkage."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.get_admin_attachment(
                    feedback_id=feedback_id,
                    attachment_id=attachment_id,
                )
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError(
                    "failed to read feedback attachment"
                ) from exc

    async def summarize_feedback(
        self,
        query: SummarizeFeedbackQuery,
    ) -> FeedbackSummary:
        """Return aggregate feedback counts over a requested window."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.summarize_feedback(query)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc

    async def get_feedback_metrics(
        self,
        query: FeedbackMetricsQuery,
    ) -> FeedbackMetrics:
        """Return dashboard feedback metrics over a requested window."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                return await repository.get_feedback_metrics(query)
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackReadError("failed to read feedback records") from exc


def get_feedback_service() -> FeedbackService:
    """Return the shared feedback service."""

    return FeedbackService(get_session_maker())
