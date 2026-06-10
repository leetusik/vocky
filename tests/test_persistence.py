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
    FeedbackDailyMetricCount,
    FeedbackListCursor,
    FeedbackQueryFilters,
    FeedbackMetricCounts,
    FeedbackMetrics,
    FeedbackMetricsQuery,
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

    assert migration_version == "20260604_2305"
    assert index_rows == [
        "ix_feedback_events_channel",
        "ix_feedback_events_conversation_id",
        "ix_feedback_events_event_at",
        "ix_feedback_events_feedback_value",
        "ix_feedback_events_ingested_at",
        "ix_feedback_events_session_id",
        "ix_feedback_events_source_product",
        "ix_feedback_events_tags_gin",
        "ix_feedback_events_target_type",
        "ix_feedback_events_trigger_type",
        "ix_feedback_events_user_id",
        "pk_feedback_events",
    ]


@pytest.mark.asyncio
async def test_service_insert_persists_values_and_db_defaults(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    record = await service.create_feedback_event(
        CreateFeedbackEvent(
            message="Billing export broke",
            source_product="vocky-cli",
            feedback_value=2,
            comment="CSV export failed after I clicked download",
            channel="web",
            source_integration="pytest",
            conversation_id="conv-1",
            session_id="sess-1",
            user_id="user-1",
            trigger_type="dislike",
            trigger_message="Thumbs down",
            trigger_metadata={"control_id": "msg-1-downvote"},
            target_type="message",
            target_id="msg-1",
            target_role="assistant",
            target_text="Click export",
            event_at=datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
            tags=("billing", "bug"),
            messages=(
                {"role": "user", "content": "Export my billing data"},
                {"role": "assistant", "content": "Click the export button"},
            ),
            used_context=({"source": "billing-export-doc", "snippet": "CSV export"},),
            source_metadata={"channel": "pytest"},
            attributes={"priority": "high"},
        )
    )

    async with get_engine().begin() as connection:
        persisted = (
            await connection.execute(
                text(
                    "SELECT message, source_product, source_integration, conversation_id, "
                    "session_id, user_id, trigger_type, trigger_message, trigger_metadata, "
                    "target_type, target_id, target_role, target_text, "
                    "feedback_value, comment, channel, event_at, tags, "
                    "messages, used_context, source_metadata, attributes, ingested_at "
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
                    "RETURNING feedback_value, comment, channel, user_id, trigger_type, "
                    "trigger_message, trigger_metadata, target_type, "
                    "target_id, target_role, target_text, tags, messages, "
                    "used_context, source_metadata, attributes, ingested_at"
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
    assert persisted["user_id"] == "user-1"
    assert persisted["trigger_type"] == "dislike"
    assert persisted["trigger_message"] == "Thumbs down"
    assert persisted["trigger_metadata"] == {"control_id": "msg-1-downvote"}
    assert record.user_id == "user-1"
    assert record.trigger_type == "dislike"
    assert record.trigger_message == "Thumbs down"
    assert record.trigger_metadata == {"control_id": "msg-1-downvote"}
    assert persisted["target_type"] == "message"
    assert persisted["target_id"] == "msg-1"
    assert persisted["target_role"] == "assistant"
    assert persisted["target_text"] == "Click export"
    assert record.target_type == "message"
    assert record.target_id == "msg-1"
    assert record.target_role == "assistant"
    assert record.target_text == "Click export"
    assert persisted["feedback_value"] == 2
    assert persisted["comment"] == "CSV export failed after I clicked download"
    assert persisted["channel"] == "web"
    assert persisted["event_at"] == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)
    assert persisted["tags"] == ["billing", "bug"]
    assert persisted["messages"] == [
        {"role": "user", "content": "Export my billing data"},
        {"role": "assistant", "content": "Click the export button"},
    ]
    assert persisted["used_context"] == [
        {"source": "billing-export-doc", "snippet": "CSV export"}
    ]
    assert persisted["source_metadata"] == {"channel": "pytest"}
    assert persisted["attributes"] == {"priority": "high"}
    assert persisted["ingested_at"] is not None

    assert defaults["feedback_value"] is None
    assert defaults["comment"] is None
    assert defaults["channel"] is None
    assert defaults["user_id"] is None
    assert defaults["trigger_type"] is None
    assert defaults["trigger_message"] is None
    assert defaults["trigger_metadata"] == {}
    assert defaults["target_type"] is None
    assert defaults["target_id"] is None
    assert defaults["target_role"] is None
    assert defaults["target_text"] is None
    assert defaults["tags"] == []
    assert defaults["messages"] == []
    assert defaults["used_context"] == []
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
            "feedback_value": 1,
            "channel": "web",
            "target_type": "message",
            "user_id": "user-1",
            "trigger_type": "like",
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
            "feedback_value": 1,
            "channel": "web",
            "target_type": "message",
            "user_id": "user-1",
            "trigger_type": "survey",
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
            "feedback_value": 2,
            "channel": "web",
            "target_type": "message",
            "user_id": "user-2",
            "trigger_type": "like",
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
                    "id, message, source_product, source_integration, feedback_value, "
                    "channel, target_type, user_id, trigger_type, conversation_id, "
                    "session_id, event_at, ingested_at, tags, source_metadata, attributes"
                    ") VALUES ("
                    ":id, :message, :source_product, :source_integration, :feedback_value, "
                    ":channel, :target_type, :user_id, :trigger_type, :conversation_id, "
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
                feedback_value=1,
                channel="web",
                target_type="message",
                user_id="user-1",
                trigger_type="like",
                tag="billing",
            ),
            limit=10,
        )
    )

    assert [record.message for record in page.records] == ["matching row"]
    assert page.records[0].tags == ("bug", "billing")


@pytest.mark.asyncio
async def test_service_list_feedback_filters_exact_target_type_and_preserves_null_unfiltered(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000021",
            "message": "legacy null target",
            "target_type": None,
            "ingested_at": datetime(2026, 4, 23, 3, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-000000000022",
            "message": "message target",
            "target_type": "message",
            "ingested_at": datetime(2026, 4, 23, 4, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-000000000023",
            "message": "surface target",
            "target_type": "surface",
            "ingested_at": datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, target_type, ingested_at"
                    ") VALUES ("
                    ":id, :message, :source_product, :target_type, :ingested_at"
                    ")"
                ),
                {
                    **row,
                    "source_product": "vocky-cli",
                },
            )

    unfiltered_page = await service.list_feedback(
        ListFeedbackQuery(filters=FeedbackQueryFilters(), limit=10)
    )
    message_page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(target_type="message"),
            limit=10,
        )
    )
    surface_page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(target_type="surface"),
            limit=10,
        )
    )

    assert [record.message for record in unfiltered_page.records] == [
        "surface target",
        "message target",
        "legacy null target",
    ]
    assert [record.message for record in message_page.records] == ["message target"]
    assert [record.message for record in surface_page.records] == ["surface target"]


@pytest.mark.asyncio
async def test_service_list_feedback_filters_identity_and_trigger_type(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000024",
            "message": "legacy null trigger",
            "user_id": None,
            "trigger_type": None,
            "ingested_at": datetime(2026, 4, 23, 3, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-000000000025",
            "message": "matching trigger",
            "user_id": "user-1",
            "trigger_type": "like",
            "ingested_at": datetime(2026, 4, 23, 4, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-000000000026",
            "message": "wrong trigger",
            "user_id": "user-1",
            "trigger_type": "survey",
            "ingested_at": datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, user_id, trigger_type, ingested_at"
                    ") VALUES ("
                    ":id, :message, :source_product, :user_id, :trigger_type, :ingested_at"
                    ")"
                ),
                {
                    **row,
                    "source_product": "vocky-cli",
                },
            )

    unfiltered_page = await service.list_feedback(
        ListFeedbackQuery(filters=FeedbackQueryFilters(), limit=10)
    )
    filtered_page = await service.list_feedback(
        ListFeedbackQuery(
            filters=FeedbackQueryFilters(user_id="user-1", trigger_type="like"),
            limit=10,
        )
    )

    assert [record.message for record in unfiltered_page.records] == [
        "wrong trigger",
        "matching trigger",
        "legacy null trigger",
    ]
    assert [record.message for record in filtered_page.records] == ["matching trigger"]


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


@pytest.mark.asyncio
async def test_service_feedback_metrics_counts_feedback_values_and_zero_fills_days(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    rows = [
        {
            "id": "00000000-0000-0000-0000-0000000000c1",
            "message": "liked",
            "feedback_value": 1,
            "ingested_at": datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-0000000000c2",
            "message": "disliked",
            "feedback_value": 2,
            "ingested_at": datetime(2026, 4, 25, 1, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-0000000000c3",
            "message": "unrated",
            "feedback_value": None,
            "ingested_at": datetime(2026, 4, 25, 2, 0, tzinfo=UTC),
        },
        {
            "id": "00000000-0000-0000-0000-0000000000c4",
            "message": "exclusive end",
            "feedback_value": 1,
            "ingested_at": datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
        },
    ]

    async with get_engine().begin() as connection:
        for row in rows:
            await connection.execute(
                text(
                    "INSERT INTO feedback_events ("
                    "id, message, source_product, feedback_value, ingested_at"
                    ") VALUES ("
                    ":id, :message, :source_product, :feedback_value, :ingested_at"
                    ")"
                ),
                {
                    **row,
                    "source_product": "vocky-cli",
                },
            )

    metrics = await service.get_feedback_metrics(
        FeedbackMetricsQuery(
            filters=FeedbackQueryFilters(
                start_ingested_at=datetime(2026, 4, 23, 0, 0, tzinfo=UTC),
                end_ingested_at=datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
            )
        )
    )

    assert metrics == FeedbackMetrics(
        totals=FeedbackMetricCounts(total=3, liked=1, disliked=1, unrated=1),
        daily_counts=(
            FeedbackDailyMetricCount(
                day=datetime(2026, 4, 23, tzinfo=UTC).date(),
                total=1,
                liked=1,
                disliked=0,
                unrated=0,
            ),
            FeedbackDailyMetricCount(
                day=datetime(2026, 4, 24, tzinfo=UTC).date(),
                total=0,
                liked=0,
                disliked=0,
                unrated=0,
            ),
            FeedbackDailyMetricCount(
                day=datetime(2026, 4, 25, tzinfo=UTC).date(),
                total=2,
                liked=0,
                disliked=1,
                unrated=1,
            ),
            FeedbackDailyMetricCount(
                day=datetime(2026, 4, 26, tzinfo=UTC).date(),
                total=0,
                liked=0,
                disliked=0,
                unrated=0,
            ),
        ),
    )
