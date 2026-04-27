"""Persistence repository for feedback events."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vocky.feedback.types import (
    CreateFeedbackEvent,
    FeedbackDailyCount,
    FeedbackDailyMetricCount,
    FeedbackEventRecord,
    FeedbackListCursor,
    FeedbackListPage,
    FeedbackMetricCounts,
    FeedbackMetrics,
    FeedbackMetricsQuery,
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
            feedback_value=payload.feedback_value,
            comment=payload.comment,
            channel=payload.channel,
            source_integration=payload.source_integration,
            conversation_id=payload.conversation_id,
            session_id=payload.session_id,
            event_at=payload.event_at,
            tags=list(payload.tags),
            messages=list(payload.messages),
            used_context=list(payload.used_context),
            source_metadata=dict(payload.source_metadata),
            attributes=dict(payload.attributes),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_record(model)

    async def get_feedback_event(self, feedback_id: UUID) -> FeedbackEventRecord | None:
        """Return one stored feedback record by ID."""

        model = await self._session.get(FeedbackEventModel, feedback_id)
        if model is None:
            return None
        return self._to_record(model)

    async def update_feedback_event(
        self,
        feedback_id: UUID,
        updates: Mapping[str, Any],
    ) -> FeedbackEventRecord | None:
        """Update a stored feedback record and return it."""

        model = await self._session.get(FeedbackEventModel, feedback_id)
        if model is None:
            return None

        for field_name, value in updates.items():
            setattr(model, field_name, value)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_record(model)

    async def delete_feedback_event(self, feedback_id: UUID) -> bool:
        """Delete a stored feedback record by ID."""

        model = await self._session.get(FeedbackEventModel, feedback_id)
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

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

    async def get_feedback_metrics(
        self,
        query: FeedbackMetricsQuery,
    ) -> FeedbackMetrics:
        """Return dashboard metrics over a requested ingest window."""

        utc_day = func.date(func.timezone("UTC", FeedbackEventModel.ingested_at))
        daily_statement = (
            select(
                utc_day.label("day"),
                func.count().label("total"),
                func.count().filter(FeedbackEventModel.feedback_value == 1).label("liked"),
                func.count().filter(FeedbackEventModel.feedback_value == 2).label("disliked"),
                func.count().filter(FeedbackEventModel.feedback_value.is_(None)).label("unrated"),
            )
            .select_from(FeedbackEventModel)
        )
        daily_statement = self._apply_query_filters(daily_statement, query.filters)
        daily_statement = daily_statement.group_by(utc_day).order_by(utc_day)

        daily_rows = (await self._session.execute(daily_statement)).all()
        counts_by_day = {
            row.day: FeedbackMetricCounts(
                total=int(row.total),
                liked=int(row.liked),
                disliked=int(row.disliked),
                unrated=int(row.unrated),
            )
            for row in daily_rows
        }

        start_ingested_at = query.filters.start_ingested_at
        end_ingested_at = query.filters.end_ingested_at
        assert start_ingested_at is not None
        assert end_ingested_at is not None

        zero_counts = FeedbackMetricCounts(total=0, liked=0, disliked=0, unrated=0)
        daily_counts = tuple(
            FeedbackDailyMetricCount(
                day=day,
                total=counts_by_day.get(day, zero_counts).total,
                liked=counts_by_day.get(day, zero_counts).liked,
                disliked=counts_by_day.get(day, zero_counts).disliked,
                unrated=counts_by_day.get(day, zero_counts).unrated,
            )
            for day in self._iter_requested_days(start_ingested_at.date(), end_ingested_at)
        )

        return FeedbackMetrics(
            totals=FeedbackMetricCounts(
                total=sum(daily_count.total for daily_count in daily_counts),
                liked=sum(daily_count.liked for daily_count in daily_counts),
                disliked=sum(daily_count.disliked for daily_count in daily_counts),
                unrated=sum(daily_count.unrated for daily_count in daily_counts),
            ),
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
        if filters.feedback_value is not None:
            statement = statement.where(
                FeedbackEventModel.feedback_value == filters.feedback_value
            )
        if filters.channel is not None:
            statement = statement.where(FeedbackEventModel.channel == filters.channel)
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
            feedback_value=model.feedback_value,
            comment=model.comment,
            channel=model.channel,
            source_integration=model.source_integration,
            conversation_id=model.conversation_id,
            session_id=model.session_id,
            event_at=model.event_at,
            ingested_at=model.ingested_at,
            tags=tuple(model.tags),
            messages=tuple(model.messages),
            used_context=tuple(model.used_context),
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
