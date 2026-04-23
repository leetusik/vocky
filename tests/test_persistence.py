"""Persistence tests against PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

from vocky.db import get_engine, get_session_maker
from vocky.feedback import CreateFeedbackEvent, FeedbackService


@pytest.mark.asyncio
async def test_migration_applies_and_expected_indexes_exist(configured_database: str) -> None:
    async with get_engine().connect() as connection:
        migration_version = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
        index_rows = (
            await connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' AND tablename = 'feedback_events' "
                    "ORDER BY indexname"
                )
            )
        ).scalars().all()

    assert migration_version == "20260423_2337"
    assert index_rows == [
        "ix_feedback_events_conversation_id",
        "ix_feedback_events_event_at",
        "ix_feedback_events_ingested_at",
        "ix_feedback_events_session_id",
        "ix_feedback_events_source_product",
        "ix_feedback_events_tags_gin",
        "pk_feedback_events",
    ]


@pytest.mark.asyncio
async def test_service_insert_persists_values_and_db_defaults(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    record = await service.create_feedback_event(
        CreateFeedbackEvent(
            message="Billing export broke",
            source_product="vocky-cli",
            source_integration="pytest",
            conversation_id="conv-1",
            session_id="sess-1",
            event_at=datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
            tags=("billing", "bug"),
            source_metadata={"channel": "pytest"},
            attributes={"priority": "high"},
        )
    )

    async with get_engine().begin() as connection:
        persisted = (
            await connection.execute(
                text(
                    "SELECT message, source_product, source_integration, conversation_id, "
                    "session_id, event_at, tags, source_metadata, attributes, ingested_at "
                    "FROM feedback_events WHERE id = :id"
                ),
                {"id": record.id},
            )
        ).mappings().one()

        defaults = (
            await connection.execute(
                text(
                    "INSERT INTO feedback_events (id, message, source_product) "
                    "VALUES (:id, :message, :source_product) "
                    "RETURNING tags, source_metadata, attributes, ingested_at"
                ),
                {
                    "id": uuid4(),
                    "message": "Default insert",
                    "source_product": "vocky-cli",
                },
            )
        ).mappings().one()

    assert persisted["message"] == "Billing export broke"
    assert persisted["source_product"] == "vocky-cli"
    assert persisted["source_integration"] == "pytest"
    assert persisted["conversation_id"] == "conv-1"
    assert persisted["session_id"] == "sess-1"
    assert persisted["event_at"] == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)
    assert persisted["tags"] == ["billing", "bug"]
    assert persisted["source_metadata"] == {"channel": "pytest"}
    assert persisted["attributes"] == {"priority": "high"}
    assert persisted["ingested_at"] is not None

    assert defaults["tags"] == []
    assert defaults["source_metadata"] == {}
    assert defaults["attributes"] == {}
    assert defaults["ingested_at"] is not None
