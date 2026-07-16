"""Persistence repository for feedback events."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vocky.feedback.types import (
    CreateFeedbackAttachment,
    CreateFeedbackComment,
    CreateFeedbackEvent,
    FeedbackAttachmentRecord,
    FeedbackCommentRecord,
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
from vocky.persistence.models import (
    FeedbackAttachmentModel,
    FeedbackCommentModel,
    FeedbackEventModel,
)

logger = logging.getLogger(__name__)


def _feedback_search_target() -> Any:
    """Build the immutable free-text search target expression.

    Concatenates the user-visible text columns with single-space separators and
    ``coalesce`` to guard NULLs, rendering as
    ``coalesce(message,'') || ' ' || coalesce(comment,'') || ' ' ||
    coalesce(target_text,'') || ' ' || coalesce(trigger_message,'')``.

    This is the **single source of truth** for the ``search`` predicate. The
    ``pg_trgm`` GIN index (migration ``20260716_1600``,
    ``ix_feedback_events_search_trgm``) indexes this exact expression so the
    planner can accelerate the ILIKE substring match. Only immutable operators
    (``||``/``coalesce``) are used — ``concat``/``concat_ws`` are merely STABLE
    and cannot back an expression index. The substring (``icontains``) predicate
    is language-agnostic: it matches Korean 조사-attached forms (``결제`` ⊂
    ``결제를``) and English uniformly, with no text-search configuration.
    """

    return (
        func.coalesce(FeedbackEventModel.message, "")
        .concat(" ")
        .concat(func.coalesce(FeedbackEventModel.comment, ""))
        .concat(" ")
        .concat(func.coalesce(FeedbackEventModel.target_text, ""))
        .concat(" ")
        .concat(func.coalesce(FeedbackEventModel.trigger_message, ""))
    )


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
            project_id=payload.project_id,
            message=payload.message,
            source_product=payload.source_product,
            feedback_value=payload.feedback_value,
            comment=payload.comment,
            channel=payload.channel,
            source_integration=payload.source_integration,
            conversation_id=payload.conversation_id,
            session_id=payload.session_id,
            user_id=payload.user_id,
            trigger_type=payload.trigger_type,
            trigger_message=payload.trigger_message,
            trigger_metadata=dict(payload.trigger_metadata),
            target_type=payload.target_type,
            target_id=payload.target_id,
            target_role=payload.target_role,
            target_text=payload.target_text,
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

    async def create_feedback_comment(
        self,
        payload: CreateFeedbackComment,
    ) -> FeedbackCommentRecord:
        """Persist an operator comment and return the stored record."""

        model = FeedbackCommentModel(
            feedback_id=payload.feedback_id,
            author=payload.author,
            body=payload.body,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_comment_record(model)

    async def list_feedback_comments(
        self,
        feedback_id: UUID,
    ) -> tuple[FeedbackCommentRecord, ...]:
        """Return one feedback event's operator comments, oldest-first."""

        statement = (
            select(FeedbackCommentModel)
            .where(FeedbackCommentModel.feedback_id == feedback_id)
            .order_by(
                FeedbackCommentModel.created_at,
                FeedbackCommentModel.id,
            )
        )
        models = (await self._session.execute(statement)).scalars().all()
        return tuple(self._to_comment_record(model) for model in models)

    async def list_comments_for_feedback_ids(
        self,
        feedback_ids: Sequence[UUID],
    ) -> dict[UUID, tuple[FeedbackCommentRecord, ...]]:
        """Return operator comments grouped by feedback id, oldest-first.

        Batched to avoid N+1 lookups when listing many feedback records.
        """

        if not feedback_ids:
            return {}

        statement = (
            select(FeedbackCommentModel)
            .where(FeedbackCommentModel.feedback_id.in_(feedback_ids))
            .order_by(
                FeedbackCommentModel.feedback_id,
                FeedbackCommentModel.created_at,
                FeedbackCommentModel.id,
            )
        )
        models = (await self._session.execute(statement)).scalars().all()

        grouped: dict[UUID, list[FeedbackCommentRecord]] = {}
        for model in models:
            grouped.setdefault(model.feedback_id, []).append(
                self._to_comment_record(model)
            )
        return {
            feedback_id: tuple(records)
            for feedback_id, records in grouped.items()
        }

    async def create_feedback_attachment(
        self,
        payload: CreateFeedbackAttachment,
    ) -> FeedbackAttachmentRecord:
        """Persist an uploaded, not-yet-linked attachment and return it."""

        model = FeedbackAttachmentModel(
            storage_key=payload.storage_key,
            content_type=payload.content_type,
            byte_size=payload.byte_size,
            filename=payload.filename,
            claimed_user_id=payload.claimed_user_id,
            claimed_source_product=payload.claimed_source_product,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_attachment_record(model)

    async def get_feedback_attachment(
        self,
        attachment_id: UUID,
    ) -> FeedbackAttachmentRecord | None:
        """Return one stored attachment by id, or None when missing."""

        model = await self._session.get(FeedbackAttachmentModel, attachment_id)
        if model is None:
            return None
        return self._to_attachment_record(model)

    async def link_attachments_to_feedback(
        self,
        feedback_id: UUID,
        attachment_ids: Sequence[UUID],
        *,
        user_id: str | None,
        source_product: str,
    ) -> int:
        """Link unlinked, scope-matching attachments to a feedback event.

        Guarded so only attachments that are still unlinked AND whose claimed
        scope matches the feedback's ``(user_id, source_product)`` are linked.
        Returns the number linked. Ids that are missing, already linked, or
        claimed by a different scope are skipped and logged, never raised — a
        misrouted or missing screenshot must not fail real feedback. The
        ``feedback_id IS NULL`` guard makes linking idempotent and blocks
        cross-feedback theft.
        """

        if not attachment_ids:
            return 0

        requested = tuple(dict.fromkeys(attachment_ids))

        if user_id is None:
            claimed_user_match = FeedbackAttachmentModel.claimed_user_id.is_(None)
        else:
            claimed_user_match = FeedbackAttachmentModel.claimed_user_id == user_id

        statement = (
            update(FeedbackAttachmentModel)
            .where(
                FeedbackAttachmentModel.id.in_(requested),
                FeedbackAttachmentModel.feedback_id.is_(None),
                FeedbackAttachmentModel.claimed_source_product == source_product,
                claimed_user_match,
            )
            .values(feedback_id=feedback_id)
            .returning(FeedbackAttachmentModel.id)
            .execution_options(synchronize_session=False)
        )
        linked = set((await self._session.execute(statement)).scalars().all())

        skipped = [aid for aid in requested if aid not in linked]
        if skipped:
            logger.warning(
                "feedback %s: skipped linking %d attachment(s) "
                "(missing, already linked, or scope mismatch): %s",
                feedback_id,
                len(skipped),
                [str(aid) for aid in skipped],
            )
        return len(linked)

    async def list_attachments_for_feedback_ids(
        self,
        feedback_ids: Sequence[UUID],
    ) -> dict[UUID, tuple[FeedbackAttachmentRecord, ...]]:
        """Return attachments grouped by feedback id, oldest-first.

        Batched to avoid N+1 lookups when listing many feedback records.
        """

        if not feedback_ids:
            return {}

        statement = (
            select(FeedbackAttachmentModel)
            .where(FeedbackAttachmentModel.feedback_id.in_(feedback_ids))
            .order_by(
                FeedbackAttachmentModel.feedback_id,
                FeedbackAttachmentModel.created_at,
                FeedbackAttachmentModel.id,
            )
        )
        models = (await self._session.execute(statement)).scalars().all()

        grouped: dict[UUID, list[FeedbackAttachmentRecord]] = {}
        for model in models:
            assert model.feedback_id is not None
            grouped.setdefault(model.feedback_id, []).append(
                self._to_attachment_record(model)
            )
        return {
            feedback_id: tuple(records)
            for feedback_id, records in grouped.items()
        }

    async def list_feedback_attachments(
        self,
        feedback_id: UUID,
    ) -> tuple[FeedbackAttachmentRecord, ...]:
        """Return one feedback event's attachments, oldest-first."""

        statement = (
            select(FeedbackAttachmentModel)
            .where(FeedbackAttachmentModel.feedback_id == feedback_id)
            .order_by(
                FeedbackAttachmentModel.created_at,
                FeedbackAttachmentModel.id,
            )
        )
        models = (await self._session.execute(statement)).scalars().all()
        return tuple(self._to_attachment_record(model) for model in models)

    async def list_storage_keys_for_feedback(
        self,
        feedback_id: UUID,
    ) -> tuple[str, ...]:
        """Return the storage keys of a feedback event's attachments."""

        statement = select(FeedbackAttachmentModel.storage_key).where(
            FeedbackAttachmentModel.feedback_id == feedback_id
        )
        keys = (await self._session.execute(statement)).scalars().all()
        return tuple(keys)

    async def get_user_attachment(
        self,
        *,
        feedback_id: UUID,
        attachment_id: UUID,
        user_id: str,
        source_product: str,
    ) -> FeedbackAttachmentRecord | None:
        """Return an attachment for an end-user download, scope-checked.

        Authorized off the LINKED feedback row's ``(user_id, source_product)``
        rather than the attachment's claimed scope, so an unlinked attachment is
        never downloadable. Returns None on any miss so the handler can answer
        404 without leaking existence.
        """

        statement = (
            select(FeedbackAttachmentModel)
            .join(
                FeedbackEventModel,
                FeedbackEventModel.id == FeedbackAttachmentModel.feedback_id,
            )
            .where(
                FeedbackAttachmentModel.id == attachment_id,
                FeedbackAttachmentModel.feedback_id == feedback_id,
                FeedbackEventModel.user_id == user_id,
                FeedbackEventModel.source_product == source_product,
            )
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_attachment_record(model) if model is not None else None

    async def get_admin_attachment(
        self,
        *,
        feedback_id: UUID,
        attachment_id: UUID,
    ) -> FeedbackAttachmentRecord | None:
        """Return an attachment for an operator download by feedback linkage."""

        statement = select(FeedbackAttachmentModel).where(
            FeedbackAttachmentModel.id == attachment_id,
            FeedbackAttachmentModel.feedback_id == feedback_id,
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_attachment_record(model) if model is not None else None

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

        if filters.project_id is not None:
            statement = statement.where(
                FeedbackEventModel.project_id == filters.project_id
            )
        if filters.project_ids is not None:
            statement = statement.where(
                FeedbackEventModel.project_id.in_(filters.project_ids)
            )
        if filters.search is not None:
            statement = statement.where(
                _feedback_search_target().icontains(filters.search, autoescape=True)
            )
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
        if filters.target_type is not None:
            statement = statement.where(FeedbackEventModel.target_type == filters.target_type)
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
        if filters.user_id is not None:
            statement = statement.where(FeedbackEventModel.user_id == filters.user_id)
        if filters.trigger_type is not None:
            statement = statement.where(FeedbackEventModel.trigger_type == filters.trigger_type)
        if filters.tag is not None:
            statement = statement.where(FeedbackEventModel.tags.contains([filters.tag]))

        return statement

    def _to_record(self, model: FeedbackEventModel) -> FeedbackEventRecord:
        """Convert a persisted model into a transport-neutral record."""

        return FeedbackEventRecord(
            id=model.id,
            project_id=model.project_id,
            message=model.message,
            source_product=model.source_product,
            feedback_value=model.feedback_value,
            comment=model.comment,
            channel=model.channel,
            source_integration=model.source_integration,
            conversation_id=model.conversation_id,
            session_id=model.session_id,
            user_id=model.user_id,
            trigger_type=model.trigger_type,
            trigger_message=model.trigger_message,
            trigger_metadata=dict(model.trigger_metadata),
            target_type=model.target_type,
            target_id=model.target_id,
            target_role=model.target_role,
            target_text=model.target_text,
            event_at=model.event_at,
            ingested_at=model.ingested_at,
            tags=tuple(model.tags),
            messages=tuple(model.messages),
            used_context=tuple(model.used_context),
            source_metadata=dict(model.source_metadata),
            attributes=dict(model.attributes),
        )

    def _to_comment_record(
        self,
        model: FeedbackCommentModel,
    ) -> FeedbackCommentRecord:
        """Convert a persisted comment model into a transport-neutral record."""

        return FeedbackCommentRecord(
            id=model.id,
            feedback_id=model.feedback_id,
            author=model.author,
            body=model.body,
            created_at=model.created_at,
        )

    def _to_attachment_record(
        self,
        model: FeedbackAttachmentModel,
    ) -> FeedbackAttachmentRecord:
        """Convert a persisted attachment model into a transport-neutral record."""

        return FeedbackAttachmentRecord(
            id=model.id,
            feedback_id=model.feedback_id,
            storage_key=model.storage_key,
            content_type=model.content_type,
            byte_size=model.byte_size,
            filename=model.filename,
            claimed_user_id=model.claimed_user_id,
            claimed_source_product=model.claimed_source_product,
            created_at=model.created_at,
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
