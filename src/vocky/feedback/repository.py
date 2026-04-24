"""Persistence repository for feedback events."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vocky.feedback.types import (
    CreateFeedbackEvent,
    FeedbackDailyCount,
    FeedbackEventRecord,
    FeedbackListCursor,
    FeedbackListPage,
    FeedbackQueryFilters,
    FeedbackSummary,
    ListFeedbackQuery,
    SummarizeFeedbackQuery,
)
from vocky.persistence.models import FeedbackEventModel


class FeedbackRepository:
    """Repository for feedback event persistence and reads."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_feedback_event(
        self,
        payload: CreateFeedbackEvent,
    ) -> FeedbackEventRecord:
        """Persist a feedback event and return the stored record."""

        model = FeedbackEventModel(
            message=payload.message,
            source_product=payload.source_product,
            source_integration=payload.source_integration,
            conversation_id=payload.conversation_id,
            session_id=payload.session_id,
            event_at=payload.event_at,
            tags=list(payload.tags),
            source_metadata=dict(payload.source_metadata),
            attributes=dict(payload.attributes),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_record(model)

    async def list_feedback(
        self,
        query: ListFeedbackQuery,
    ) -> FeedbackListPage:
        """Return a cursor-paginated list of stored feedback records."""

        statement = select(FeedbackEventModel)
        statement = self._apply_query_filters(statement, query.filters)

        if query.cursor is not None:
            statement = statement.where(
                or_(
                    FeedbackEventModel.ingested_at < query.cursor.ingested_at,
                    and_(
                        FeedbackEventModel.ingested_at == query.cursor.ingested_at,
                        FeedbackEventModel.id < query.cursor.id,
                    ),
                )
            )

        statement = statement.order_by(
            FeedbackEventModel.ingested_at.desc(),
            FeedbackEventModel.id.desc(),
        ).limit(query.limit + 1)

        models = (await self._session.execute(statement)).scalars().all()
        has_next_page = len(models) > query.limit
        page_models = models[: query.limit]

        next_cursor = None
        if has_next_page and page_models:
            last_model = page_models[-1]
            next_cursor = FeedbackListCursor(
                ingested_at=last_model.ingested_at,
                id=last_model.id,
            )

        return FeedbackListPage(
            records=tuple(self._to_record(model) for model in page_models),
            next_cursor=next_cursor,
        )

    async def summarize_feedback(
        self,
        query: SummarizeFeedbackQuery,
    ) -> FeedbackSummary:
        """Return aggregate feedback counts over a requested ingest window."""

        total_statement = select(func.count()).select_from(FeedbackEventModel)
        total_statement = self._apply_query_filters(total_statement, query.filters)
        total_count = int((await self._session.execute(total_statement)).scalar_one())

        utc_day = func.date(func.timezone("UTC", FeedbackEventModel.ingested_at))
        daily_statement = (
            select(
                utc_day.label("day"),
                func.count().label("count"),
            )
            .select_from(FeedbackEventModel)
        )
        daily_statement = self._apply_query_filters(daily_statement, query.filters)
        daily_statement = daily_statement.group_by(utc_day).order_by(utc_day)

        daily_rows = (await self._session.execute(daily_statement)).all()
        counts_by_day = {
            row.day: int(row.count)
            for row in daily_rows
        }

        start_ingested_at = query.filters.start_ingested_at
        end_ingested_at = query.filters.end_ingested_at
        assert start_ingested_at is not None
        assert end_ingested_at is not None

        daily_counts = tuple(
            FeedbackDailyCount(
                day=day,
                count=counts_by_day.get(day, 0),
            )
            for day in self._iter_requested_days(start_ingested_at.date(), end_ingested_at)
        )

        return FeedbackSummary(
            total_count=total_count,
            daily_counts=daily_counts,
        )

    def _apply_query_filters(
        self,
        statement: Select[Any],
        filters: FeedbackQueryFilters,
    ) -> Select[Any]:
        """Apply the supported read filters to a statement."""

        if filters.start_ingested_at is not None:
            statement = statement.where(
                FeedbackEventModel.ingested_at >= filters.start_ingested_at
            )
        if filters.end_ingested_at is not None:
            statement = statement.where(FeedbackEventModel.ingested_at < filters.end_ingested_at)
        if filters.source_product is not None:
            statement = statement.where(
                FeedbackEventModel.source_product == filters.source_product
            )
        if filters.source_integration is not None:
            statement = statement.where(
                FeedbackEventModel.source_integration == filters.source_integration
            )
        if filters.conversation_id is not None:
            statement = statement.where(
                FeedbackEventModel.conversation_id == filters.conversation_id
            )
        if filters.session_id is not None:
            statement = statement.where(FeedbackEventModel.session_id == filters.session_id)
        if filters.tag is not None:
            statement = statement.where(FeedbackEventModel.tags.contains([filters.tag]))

        return statement

    def _to_record(self, model: FeedbackEventModel) -> FeedbackEventRecord:
        """Convert a persisted model into a transport-neutral record."""

        return FeedbackEventRecord(
            id=model.id,
            message=model.message,
            source_product=model.source_product,
            source_integration=model.source_integration,
            conversation_id=model.conversation_id,
            session_id=model.session_id,
            event_at=model.event_at,
            ingested_at=model.ingested_at,
            tags=tuple(model.tags),
            source_metadata=dict(model.source_metadata),
            attributes=dict(model.attributes),
        )

    def _iter_requested_days(
        self,
        start_day: date,
        end_ingested_at: datetime,
    ) -> tuple[date, ...]:
        """Return the UTC day series covered by an exclusive end timestamp."""

        last_day = (end_ingested_at - timedelta(microseconds=1)).date()
        current = start_day
        days: list[date] = []

        while current <= last_day:
            days.append(current)
            current += timedelta(days=1)

        return tuple(days)
