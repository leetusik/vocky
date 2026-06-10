"""Persistence tests for the operator comment store."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from vocky.db import get_engine, get_session_maker
from vocky.feedback import (
    CreateFeedbackComment,
    CreateFeedbackEvent,
    FeedbackService,
)
from vocky.feedback.repository import FeedbackRepository


async def _create_feedback(service: FeedbackService, *, message: str) -> UUID:
    """Persist a minimal feedback event and return its id."""

    record = await service.create_feedback_event(
        CreateFeedbackEvent(message=message, source_product="comment-tests")
    )
    return record.id


async def _insert_comment(
    *,
    feedback_id: UUID,
    body: str,
    created_at: datetime,
    author: str | None = None,
) -> None:
    """Insert one comment with an explicit created_at for deterministic ordering."""

    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_comments (id, feedback_id, author, body, created_at) "
                "VALUES (:id, :feedback_id, :author, :body, :created_at)"
            ),
            {
                "id": uuid4(),
                "feedback_id": feedback_id,
                "author": author,
                "body": body,
                "created_at": created_at,
            },
        )


@pytest.mark.asyncio
async def test_create_feedback_comment_persists_fields(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="needs operator follow-up")

    with_author = await service.create_feedback_comment(
        CreateFeedbackComment(
            feedback_id=feedback_id,
            body="Escalated to billing team",
            author="ops-jane",
        )
    )
    without_author = await service.create_feedback_comment(
        CreateFeedbackComment(feedback_id=feedback_id, body="Awaiting reply")
    )

    assert isinstance(with_author.id, UUID)
    assert with_author.feedback_id == feedback_id
    assert with_author.author == "ops-jane"
    assert with_author.body == "Escalated to billing team"
    assert with_author.created_at.tzinfo is not None
    assert without_author.author is None
    assert without_author.body == "Awaiting reply"
    assert without_author.id != with_author.id


@pytest.mark.asyncio
async def test_list_feedback_comments_orders_oldest_first(configured_database: str) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="ordering check")

    # Insert newest-first to prove ordering is by created_at, not insertion order.
    await _insert_comment(
        feedback_id=feedback_id,
        body="third",
        created_at=datetime(2026, 6, 3, 9, 0, tzinfo=UTC),
    )
    await _insert_comment(
        feedback_id=feedback_id,
        body="first",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        author="ops-amy",
    )
    await _insert_comment(
        feedback_id=feedback_id,
        body="second",
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
    )

    comments = await service.list_feedback_comments(feedback_id)

    assert [comment.body for comment in comments] == ["first", "second", "third"]
    assert comments[0].author == "ops-amy"
    assert comments[1].author is None


@pytest.mark.asyncio
async def test_list_feedback_comments_empty_returns_empty_tuple(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="no comments yet")

    assert await service.list_feedback_comments(feedback_id) == ()


@pytest.mark.asyncio
async def test_feedback_comments_cascade_on_feedback_delete(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_id = await _create_feedback(service, message="delete cascades comments")

    await service.create_feedback_comment(
        CreateFeedbackComment(feedback_id=feedback_id, body="comment one")
    )
    await service.create_feedback_comment(
        CreateFeedbackComment(feedback_id=feedback_id, body="comment two")
    )

    async with get_engine().connect() as connection:
        before = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM feedback_comments WHERE feedback_id = :fid"
                ),
                {"fid": feedback_id},
            )
        ).scalar_one()
    assert before == 2

    deleted, _ = await service.delete_feedback_event(feedback_id)
    assert deleted is True

    async with get_engine().connect() as connection:
        after = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM feedback_comments WHERE feedback_id = :fid"
                ),
                {"fid": feedback_id},
            )
        ).scalar_one()
    assert after == 0


@pytest.mark.asyncio
async def test_list_comments_for_feedback_ids_groups_oldest_first(
    configured_database: str,
) -> None:
    service = FeedbackService(get_session_maker())
    feedback_a = await _create_feedback(service, message="feedback a")
    feedback_b = await _create_feedback(service, message="feedback b")
    feedback_c = await _create_feedback(service, message="feedback c (no comments)")

    await _insert_comment(
        feedback_id=feedback_a,
        body="a-second",
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
    )
    await _insert_comment(
        feedback_id=feedback_a,
        body="a-first",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
    )
    await _insert_comment(
        feedback_id=feedback_b,
        body="b-only",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
    )

    async with get_session_maker()() as session:
        repository = FeedbackRepository(session)
        grouped = await repository.list_comments_for_feedback_ids(
            [feedback_a, feedback_b, feedback_c]
        )
        empty = await repository.list_comments_for_feedback_ids([])

    assert [comment.body for comment in grouped[feedback_a]] == ["a-first", "a-second"]
    assert [comment.body for comment in grouped[feedback_b]] == ["b-only"]
    assert feedback_c not in grouped
    assert empty == {}
