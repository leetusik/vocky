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
    CreateFeedbackEvent,
    FeedbackEventRecord,
    FeedbackListPage,
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

    async def delete_feedback_event(self, feedback_id: UUID) -> bool:
        """Delete one feedback record by ID."""

        async with self._session_maker() as session:
            repository = FeedbackRepository(session)

            try:
                deleted = await repository.delete_feedback_event(feedback_id)
                await session.commit()
                return deleted
            except SQLAlchemyError as exc:
                await session.rollback()
                raise FeedbackPersistenceError(
                    "failed to persist feedback event"
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


def get_feedback_service() -> FeedbackService:
    """Return the shared feedback service."""

    return FeedbackService(get_session_maker())
