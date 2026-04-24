"""Transport-neutral feedback service."""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
