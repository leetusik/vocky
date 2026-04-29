"""Validation tests for feedback read-tool normalization."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from vocky.tools.list_feedback import ListFeedbackInput, normalize_payload
from vocky.tools.list_liked_conversations import (
    ListLikedConversationsInput,
    normalize_payload as normalize_liked_payload,
)
from vocky.tools.summarize_feedback import SummarizeFeedbackInput, normalize_payload as normalize_summary_payload
from vocky.tools.query_feedback_common import (
    DEFAULT_LIST_LIMIT,
    FeedbackQueryValidationError,
    decode_cursor,
    encode_cursor,
)
from vocky.feedback import FeedbackListCursor


def make_list_input(**overrides: object) -> ListFeedbackInput:
    """Create a default raw list input for tests."""

    data = {
        "start_ingested_at": None,
        "end_ingested_at": None,
        "source_product": None,
        "source_integration": None,
        "conversation_id": None,
        "session_id": None,
        "feedback_value": None,
        "channel": None,
        "target_type": None,
        "tag": None,
        "limit": None,
        "cursor": None,
    }
    data.update(overrides)
    return ListFeedbackInput(**data)


def make_summary_input(**overrides: object) -> SummarizeFeedbackInput:
    """Create a default raw summary input for tests."""

    data = {
        "start_ingested_at": "2026-04-23T00:00:00Z",
        "end_ingested_at": "2026-04-25T00:00:00Z",
        "source_product": None,
        "source_integration": None,
        "conversation_id": None,
        "session_id": None,
        "feedback_value": None,
        "channel": None,
        "target_type": None,
        "tag": None,
    }
    data.update(overrides)
    return SummarizeFeedbackInput(**data)


def make_liked_input(**overrides: object) -> ListLikedConversationsInput:
    """Create a default raw liked-conversation input for tests."""

    data = {
        "start_ingested_at": None,
        "end_ingested_at": None,
        "source_product": None,
        "source_integration": None,
        "conversation_id": None,
        "session_id": None,
        "channel": None,
        "target_type": None,
        "tag": None,
        "limit": None,
        "cursor": None,
    }
    data.update(overrides)
    return ListLikedConversationsInput(**data)


def test_blank_tag_is_rejected_for_listing() -> None:
    with pytest.raises(FeedbackQueryValidationError, match="tag must not be blank"):
        normalize_payload(make_list_input(tag="   "))


def test_invalid_time_window_is_rejected_for_listing() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="start_ingested_at must be before end_ingested_at",
    ):
        normalize_payload(
            make_list_input(
                start_ingested_at="2026-04-23T00:00:00Z",
                end_ingested_at="2026-04-23T00:00:00Z",
            )
        )


def test_invalid_limit_is_rejected_for_listing() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="limit must be between 1 and 100",
    ):
        normalize_payload(make_list_input(limit=0))


def test_invalid_feedback_value_is_rejected_for_listing() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="feedback_value must be 1 for like or 2 for dislike",
    ):
        normalize_payload(make_list_input(feedback_value=4))


def test_invalid_target_type_is_rejected_for_listing() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="target_type must be one of: message, conversation, surface",
    ):
        normalize_payload(make_list_input(target_type="answer"))


def test_invalid_cursor_is_rejected_for_listing() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="cursor must be a valid list_feedback cursor",
    ):
        normalize_payload(make_list_input(cursor="not-a-cursor"))


def test_listing_normalization_collapses_blank_optional_filters() -> None:
    query = normalize_payload(
        make_list_input(
            source_product="  ",
            source_integration=" pytest ",
            conversation_id=" conv-1 ",
            session_id="   ",
            feedback_value=1,
            channel=" web ",
            target_type=" message ",
            limit=None,
        )
    )

    assert query.filters.source_product is None
    assert query.filters.source_integration == "pytest"
    assert query.filters.conversation_id == "conv-1"
    assert query.filters.session_id is None
    assert query.filters.feedback_value == 1
    assert query.filters.channel == "web"
    assert query.filters.target_type == "message"
    assert query.limit == DEFAULT_LIST_LIMIT


def test_listing_normalization_collapses_blank_target_type() -> None:
    query = normalize_payload(make_list_input(target_type="   "))

    assert query.filters.target_type is None


def test_cursor_round_trip_preserves_utc_timestamp_and_id() -> None:
    cursor = FeedbackListCursor(
        ingested_at=datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
        id=UUID("00000000-0000-0000-0000-0000000000ab"),
    )

    encoded = encode_cursor(cursor)
    decoded = decode_cursor(encoded)

    assert decoded == cursor


def test_summary_requires_start_ingested_at() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="start_ingested_at is required",
    ):
        normalize_summary_payload(make_summary_input(start_ingested_at=None))


def test_summary_requires_end_ingested_at() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="end_ingested_at is required",
    ):
        normalize_summary_payload(make_summary_input(end_ingested_at=None))


def test_summary_rejects_invalid_time_window() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="start_ingested_at must be before end_ingested_at",
    ):
        normalize_summary_payload(
            make_summary_input(
                start_ingested_at="2026-04-24T00:00:00Z",
                end_ingested_at="2026-04-24T00:00:00Z",
            )
        )


def test_invalid_feedback_value_is_rejected_for_summary() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="feedback_value must be 1 for like or 2 for dislike",
    ):
        normalize_summary_payload(make_summary_input(feedback_value=0))


def test_invalid_target_type_is_rejected_for_summary() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="target_type must be one of: message, conversation, surface",
    ):
        normalize_summary_payload(make_summary_input(target_type="thread"))


def test_summary_normalization_trims_optional_filters() -> None:
    query = normalize_summary_payload(
        make_summary_input(
            source_product=" vocky-cli ",
            source_integration=" ",
            conversation_id=" conv-1 ",
            session_id=" ",
            feedback_value=2,
            channel=" mobile ",
            target_type=" surface ",
            tag=" billing ",
        )
    )

    assert query.filters.source_product == "vocky-cli"
    assert query.filters.source_integration is None
    assert query.filters.conversation_id == "conv-1"
    assert query.filters.session_id is None
    assert query.filters.feedback_value == 2
    assert query.filters.channel == "mobile"
    assert query.filters.target_type == "surface"
    assert query.filters.tag == "billing"


def test_liked_conversation_normalization_trims_target_type() -> None:
    query = normalize_liked_payload(make_liked_input(target_type=" conversation "))

    assert query.filters.target_type == "conversation"


def test_invalid_target_type_is_rejected_for_liked_conversations() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="target_type must be one of: message, conversation, surface",
    ):
        normalize_liked_payload(make_liked_input(target_type="page"))
