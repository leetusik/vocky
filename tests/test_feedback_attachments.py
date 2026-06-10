"""Persistence tests for the feedback attachment store."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from vocky.db import get_engine, get_session_maker
from vocky.feedback import (
    CreateFeedbackAttachment,
    CreateFeedbackEvent,
    FeedbackService,
)
from vocky.feedback.repository import FeedbackRepository
from vocky.feedback.service import FeedbackPersistenceError
from vocky.feedback.types import FeedbackQueryFilters, ListFeedbackQuery


async def _create_feedback(
    service: FeedbackService,
    *,
    message: str,
    user_id: str | None = None,
    source_product: str = "attach-tests",
) -> UUID:
    """Persist a minimal feedback event and return its id."""

    record = await service.create_feedback_event(
        CreateFeedbackEvent(
            message=message,
            source_product=source_product,
            user_id=user_id,
        )
    )
    return record.id


async def _create_attachment(
    service: FeedbackService,
    *,
    claimed_user_id: str | None,
    claimed_source_product: str,
    content_type: str = "image/png",
    byte_size: int = 3,
    filename: str | None = None,
) -> UUID:
    """Persist an unlinked attachment and return its id."""

    record = await service.create_unlinked_attachment(
        CreateFeedbackAttachment(
            storage_key=str(uuid4()),
            content_type=content_type,
            byte_size=byte_size,
            filename=filename,
            claimed_user_id=claimed_user_id,
            claimed_source_product=claimed_source_product,
        )
    )
    return record.id


async def _link(
    feedback_id: UUID,
    attachment_ids: list[UUID],
    *,
    user_id: str | None,
    source_product: str,
) -> int:
    """Link attachments through the repository, committing the result."""

    async with get_session_maker()() as session:
        repository = FeedbackRepository(session)
        count = await repository.link_attachments_to_feedback(
            feedback_id,
            attachment_ids,
            user_id=user_id,
            source_product=source_product,
        )
        await session.commit()
    return count


async def _insert_attachment(
    *,
    feedback_id: UUID | None,
    created_at: datetime,
    storage_key: str,
    claimed_source_product: str = "attach-tests",
    claimed_user_id: str | None = None,
) -> None:
    """Insert one attachment with an explicit created_at for deterministic order."""

    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_attachments ("
                "id, feedback_id, storage_key, content_type, byte_size, filename, "
                "claimed_user_id, claimed_source_product, created_at"
                ") VALUES ("
                ":id, :feedback_id, :storage_key, 'image/png', 3, NULL, "
                ":claimed_user_id, :claimed_source_product, :created_at)"
            ),
            {
                "id": uuid4(),
                "feedback_id": feedback_id,
                "storage_key": storage_key,
                "claimed_user_id": claimed_user_id,
                "claimed_source_product": claimed_source_product,
                "created_at": created_at,
            },
        )


@pytest.mark.asyncio
async def test_create_unlinked_attachment_persists_fields(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    record = await service.create_unlinked_attachment(
        CreateFeedbackAttachment(
            storage_key="object-key",
            content_type="image/png",
            byte_size=2048,
            filename="screenshot.png",
            claimed_user_id="user-1",
            claimed_source_product="changple5",
        )
    )

    assert isinstance(record.id, UUID)
    assert record.feedback_id is None
    assert record.storage_key == "object-key"
    assert record.content_type == "image/png"
    assert record.byte_size == 2048
    assert record.filename == "screenshot.png"
    assert record.claimed_user_id == "user-1"
    assert record.claimed_source_product == "changple5"
    assert record.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_get_feedback_attachment_unknown_returns_none(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())

    assert await service.get_feedback_attachment(uuid4()) is None


@pytest.mark.asyncio
async def test_link_attachments_links_matching_scope(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(
        service, message="with screenshot", user_id="user-1"
    )
    attachment_id = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="attach-tests"
    )

    linked = await _link(
        feedback_id,
        [attachment_id],
        user_id="user-1",
        source_product="attach-tests",
    )

    assert linked == 1
    record = await service.get_feedback_attachment(attachment_id)
    assert record is not None
    assert record.feedback_id == feedback_id


@pytest.mark.asyncio
async def test_link_attachments_idempotent(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="m", user_id="user-1")
    attachment_id = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="attach-tests"
    )

    first = await _link(
        feedback_id, [attachment_id], user_id="user-1", source_product="attach-tests"
    )
    second = await _link(
        feedback_id, [attachment_id], user_id="user-1", source_product="attach-tests"
    )

    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_link_skips_scope_mismatch(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="m", user_id="user-1")
    wrong_user = await _create_attachment(
        service, claimed_user_id="user-2", claimed_source_product="attach-tests"
    )
    wrong_product = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="other-product"
    )

    linked = await _link(
        feedback_id,
        [wrong_user, wrong_product],
        user_id="user-1",
        source_product="attach-tests",
    )

    assert linked == 0
    assert (await service.get_feedback_attachment(wrong_user)).feedback_id is None
    assert (await service.get_feedback_attachment(wrong_product)).feedback_id is None


@pytest.mark.asyncio
async def test_link_blocks_cross_feedback_theft(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_a = await _create_feedback(service, message="a", user_id="user-1")
    feedback_b = await _create_feedback(service, message="b", user_id="user-1")
    attachment_id = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="attach-tests"
    )

    await _link(
        feedback_a, [attachment_id], user_id="user-1", source_product="attach-tests"
    )
    stolen = await _link(
        feedback_b, [attachment_id], user_id="user-1", source_product="attach-tests"
    )

    assert stolen == 0
    record = await service.get_feedback_attachment(attachment_id)
    assert record.feedback_id == feedback_a


@pytest.mark.asyncio
async def test_link_anonymous_user_via_is_null(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="anon", user_id=None)
    attachment_id = await _create_attachment(
        service, claimed_user_id=None, claimed_source_product="attach-tests"
    )

    linked = await _link(
        feedback_id, [attachment_id], user_id=None, source_product="attach-tests"
    )

    assert linked == 1
    assert (await service.get_feedback_attachment(attachment_id)).feedback_id == feedback_id


@pytest.mark.asyncio
async def test_create_feedback_event_with_attachments_links(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    attachment_id = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="changple5"
    )

    record = await service.create_feedback_event_with_attachments(
        CreateFeedbackEvent(
            message="captured with image",
            source_product="changple5",
            user_id="user-1",
            attachment_ids=(attachment_id,),
        )
    )

    stored = await service.get_feedback_attachment(attachment_id)
    assert stored.feedback_id == record.id
    linked = await service.list_feedback_attachments(record.id)
    assert [item.id for item in linked] == [attachment_id]


@pytest.mark.asyncio
async def test_create_feedback_event_with_attachments_rolls_back_on_failure(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FeedbackService(get_session_maker())
    attachment_id = await _create_attachment(
        service, claimed_user_id="user-1", claimed_source_product="changple5"
    )

    async def boom(self: FeedbackRepository, *args: object, **kwargs: object) -> int:
        raise SQLAlchemyError("forced link failure")

    monkeypatch.setattr(FeedbackRepository, "link_attachments_to_feedback", boom)

    with pytest.raises(FeedbackPersistenceError):
        await service.create_feedback_event_with_attachments(
            CreateFeedbackEvent(
                message="should roll back",
                source_product="changple5",
                user_id="user-1",
                attachment_ids=(attachment_id,),
            )
        )

    # The feedback event insert was rolled back with the failed link.
    page = await service.list_feedback(
        ListFeedbackQuery(limit=50, filters=FeedbackQueryFilters(source_product="changple5"))
    )
    assert page.records == ()
    # The attachment stays unlinked.
    assert (await service.get_feedback_attachment(attachment_id)).feedback_id is None


@pytest.mark.asyncio
async def test_list_attachments_for_feedback_ids_groups_oldest_first(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_a = await _create_feedback(service, message="a")
    feedback_b = await _create_feedback(service, message="b")
    feedback_c = await _create_feedback(service, message="c (no attachments)")

    await _insert_attachment(
        feedback_id=feedback_a,
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
        storage_key="a-second",
    )
    await _insert_attachment(
        feedback_id=feedback_a,
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        storage_key="a-first",
    )
    await _insert_attachment(
        feedback_id=feedback_b,
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        storage_key="b-only",
    )

    async with get_session_maker()() as session:
        repository = FeedbackRepository(session)
        grouped = await repository.list_attachments_for_feedback_ids(
            [feedback_a, feedback_b, feedback_c]
        )
        empty = await repository.list_attachments_for_feedback_ids([])

    assert [item.storage_key for item in grouped[feedback_a]] == ["a-first", "a-second"]
    assert [item.storage_key for item in grouped[feedback_b]] == ["b-only"]
    assert feedback_c not in grouped
    assert empty == {}


@pytest.mark.asyncio
async def test_list_storage_keys_for_feedback(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="m")
    await _insert_attachment(
        feedback_id=feedback_id,
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        storage_key="key-1",
    )
    await _insert_attachment(
        feedback_id=feedback_id,
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
        storage_key="key-2",
    )

    async with get_session_maker()() as session:
        repository = FeedbackRepository(session)
        keys = await repository.list_storage_keys_for_feedback(feedback_id)

    assert set(keys) == {"key-1", "key-2"}


@pytest.mark.asyncio
async def test_attachments_cascade_on_feedback_delete(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="delete cascades attachments")
    await _insert_attachment(
        feedback_id=feedback_id,
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        storage_key="key-1",
    )

    async with get_engine().connect() as connection:
        before = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM feedback_attachments WHERE feedback_id = :fid"
                ),
                {"fid": feedback_id},
            )
        ).scalar_one()
    assert before == 1

    deleted, _ = await service.delete_feedback_event(feedback_id)
    assert deleted is True

    async with get_engine().connect() as connection:
        after = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM feedback_attachments WHERE feedback_id = :fid"
                ),
                {"fid": feedback_id},
            )
        ).scalar_one()
    assert after == 0
