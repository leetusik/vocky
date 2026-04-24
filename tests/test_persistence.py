"""Persistence tests against PostgreSQL."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from vocky.db import get_engine, get_session_maker
from vocky.feedback import (
    CreateFeedbackEvent,
    FeedbackDailyCount,
    FeedbackListCursor,
    FeedbackQueryFilters,
    FeedbackSummary,
    FeedbackService,
    ListFeedbackQuery,
    SummarizeFeedbackQuery,
)


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


@pytest.mark.asyncio
async def test_service_list_feedback_orders_by_ingested_at_then_id_and_paginates(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "message": "oldest",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-a",
            "session_id": "sess-a",
            "event_at": datetime(2026, 4, 22, 6, 0, tzinfo=UTC),
            "ingested_at": datetime(2026, 4, 22, 7, 0, tzinfo=UTC),
            "tags": ["bug"],
            "source_metadata": {"channel": "seed"},
            "attributes": {"priority": "low"},
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "message": "same time lower id",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-a",
            "session_id": "sess-a",
            "event_at": datetime(2026, 4, 23, 6, 0, tzinfo=UTC),
            "ingested_at": datetime(2026, 4, 23, 7, 0, tzinfo=UTC),
            "tags": ["bug"],
            "source_metadata": {"channel": "seed"},
            "attributes": {"priority": "medium"},
        },
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "message": "same time higher id",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-a",
            "session_id": "sess-a",
            "event_at": datetime(2026, 4, 23, 8, 0, tzinfo=UTC),
            "ingested_at": datetime(2026, 4, 23, 7, 0, tzinfo=UTC),
            "tags": ["bug", "smoke"],
            "source_metadata": {"channel": "seed"},
            "attributes": {"priority": "high"},
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, source_integration, conversation_id, "
                    "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                    ") VALUES ("
                    ":id, :message, :source_product, :source_integration, :conversation_id, "
                    ":session_id, :event_at, :ingested_at, :tags, "
                    "CAST(:source_metadata AS jsonb), CAST(:attributes AS jsonb)"
                    ")"
                ),
                {
                    **row,
                    "source_metadata": json.dumps(row["source_metadata"]),
                    "attributes": json.dumps(row["attributes"]),
                },
            )

    first_page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(source_product="vocky-cli"),
            limit=2,
        )
    )

    assert [record.message for record in first_page.records] == [
        "same time higher id",
        "same time lower id",
    ]
    assert first_page.next_cursor == FeedbackListCursor(
        ingested_at=datetime(2026, 4, 23, 7, 0, tzinfo=UTC),
        id=UUID("00000000-0000-0000-0000-000000000002"),
    )

    second_page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(source_product="vocky-cli"),
            limit=2,
            cursor=first_page.next_cursor,
        )
    )

    assert [record.message for record in second_page.records] == ["oldest"]
    assert second_page.next_cursor is None


@pytest.mark.asyncio
async def test_service_list_feedback_applies_supported_filters(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000011",
            "message": "matching row",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 23, 0, 30, tzinfo=UTC),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000012",
            "message": "wrong tag",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 23, 1, 0, tzinfo=UTC),
            "tags": ["praise"],
            "source_metadata": {},
            "attributes": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000013",
            "message": "wrong conversation",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-2",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 23, 1, 30, tzinfo=UTC),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, source_integration, conversation_id, "
                    "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                    ") VALUES ("
                    ":id, :message, :source_product, :source_integration, :conversation_id, "
                    ":session_id, :event_at, :ingested_at, :tags, "
                    "CAST(:source_metadata AS jsonb), CAST(:attributes AS jsonb)"
                    ")"
                ),
                {
                    **row,
                    "source_metadata": json.dumps(row["source_metadata"]),
                    "attributes": json.dumps(row["attributes"]),
                },
            )

    page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(
                start_ingested_at=datetime(2026, 4, 23, 0, 0, tzinfo=UTC),
                end_ingested_at=datetime(2026, 4, 23, 1, 0, tzinfo=UTC),
                source_product="vocky-cli",
                source_integration="pytest",
                conversation_id="conv-1",
                session_id="sess-1",
                tag="billing",
            ),
            limit=10,
        )
    )

    assert [record.message for record in page.records] == ["matching row"]
    assert page.records[0].tags == ("bug", "billing")


@pytest.mark.asyncio
async def test_service_summarize_feedback_zero_fills_utc_day_series(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000031",
            "message": "utc day one",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 23, 2, 0, tzinfo=UTC),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000032",
            "message": "same utc day from +09",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 24, 0, 30, tzinfo=timezone(timedelta(hours=9))),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000033",
            "message": "utc day three",
            "source_product": "vocky-cli",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 25, 5, 0, tzinfo=UTC),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
        {
            "id": "00000000-0000-0000-0000-000000000034",
            "message": "filtered out",
            "source_product": "other-product",
            "source_integration": "pytest",
            "conversation_id": "conv-1",
            "session_id": "sess-1",
            "event_at": None,
            "ingested_at": datetime(2026, 4, 24, 8, 0, tzinfo=UTC),
            "tags": ["bug", "billing"],
            "source_metadata": {},
            "attributes": {},
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, source_integration, conversation_id, "
                    "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                    ") VALUES ("
                    ":id, :message, :source_product, :source_integration, :conversation_id, "
                    ":session_id, :event_at, :ingested_at, :tags, "
                    "CAST(:source_metadata AS jsonb), CAST(:attributes AS jsonb)"
                    ")"
                ),
                {
                    **row,
                    "source_metadata": json.dumps(row["source_metadata"]),
                    "attributes": json.dumps(row["attributes"]),
                },
            )

    summary = await service.summarize_feedback(
        SummarizeFeedbackQuery(
            filters=FeedbackQueryFilters(
                start_ingested_at=datetime(2026, 4, 23, 0, 0, tzinfo=UTC),
                end_ingested_at=datetime(2026, 4, 26, 0, 0, tzinfo=UTC),
                source_product="vocky-cli",
                source_integration="pytest",
                conversation_id="conv-1",
                session_id="sess-1",
                tag="billing",
            )
        )
    )

    assert summary == FeedbackSummary(
        total_count=3,
        daily_counts=(
            FeedbackDailyCount(day=datetime(2026, 4, 23, tzinfo=UTC).date(), count=2),
            FeedbackDailyCount(day=datetime(2026, 4, 24, tzinfo=UTC).date(), count=0),
            FeedbackDailyCount(day=datetime(2026, 4, 25, tzinfo=UTC).date(), count=1),
        ),
    )
