"""Persistence repository for feedback events."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from vocky.feedback.types import CreateFeedbackEvent, FeedbackEventRecord
from vocky.persistence.models import FeedbackEventModel


class FeedbackRepository:
    """Repository for feedback event writes."""

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
