"""Validation tests for the shared feedback read-query helpers.

These helpers back the public and admin REST read surfaces (``vocky.api`` and
``vocky.admin_api``) after the agent read tools were retired, so they are
exercised directly here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from vocky.feedback import FeedbackListCursor
from vocky.tools.query_feedback_common import (
    DEFAULT_LIST_LIMIT,
    FeedbackQueryValidationError,
    decode_cursor,
    encode_cursor,
    normalize_feedback_value,
    normalize_limit,
    normalize_optional_text,
    normalize_recorded_by_filter,
    normalize_tag,
    normalize_target_type_filter,
    normalize_trigger_type_filter,
    parse_timestamp,
    validate_time_window,
)


def test_blank_tag_is_rejected() -> None:
    with pytest.raises(FeedbackQueryValidationError, match="tag must not be blank"):
        normalize_tag("   ")


def test_optional_text_collapses_blank_to_none_and_trims() -> None:
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text(None) is None
    assert normalize_optional_text(" conv-1 ") == "conv-1"


def test_invalid_time_window_is_rejected() -> None:
    start = parse_timestamp("2026-04-23T00:00:00Z", field_name="start_ingested_at")
    with pytest.raises(
        FeedbackQueryValidationError,
        match="start_ingested_at must be before end_ingested_at",
    ):
        validate_time_window(start, start)


def test_default_and_out_of_range_limits() -> None:
    assert normalize_limit(None) == DEFAULT_LIST_LIMIT
    with pytest.raises(FeedbackQueryValidationError, match="limit must be between 1 and 100"):
        normalize_limit(0)


def test_invalid_feedback_value_is_rejected() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="feedback_value must be 1 for like or 2 for dislike",
    ):
        normalize_feedback_value(4)


def test_invalid_target_type_filter_is_rejected() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="target_type must be one of: message, conversation, surface",
    ):
        normalize_target_type_filter("answer")


def test_blank_target_type_filter_collapses_to_none() -> None:
    assert normalize_target_type_filter("   ") is None


def test_invalid_trigger_type_filter_is_rejected() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="trigger_type must be one of: like, dislike, comment, rating, survey, manual, other",
    ):
        normalize_trigger_type_filter("thumbs-up")


def test_recorded_by_filter_accepts_the_closed_vocabulary_and_rejects_the_rest() -> None:
    assert normalize_recorded_by_filter(" agent ") == "agent"
    assert normalize_recorded_by_filter("human") == "human"
    # Absent or blank means "no filter", never "only unspecified rows".
    assert normalize_recorded_by_filter(None) is None
    assert normalize_recorded_by_filter("   ") is None
    with pytest.raises(
        FeedbackQueryValidationError,
        match="recorded_by must be one of: agent, human",
    ):
        normalize_recorded_by_filter("robot")


def test_invalid_cursor_is_rejected() -> None:
    with pytest.raises(
        FeedbackQueryValidationError,
        match="cursor must be a valid list_feedback cursor",
    ):
        decode_cursor("not-a-cursor")


def test_cursor_round_trip_preserves_utc_timestamp_and_id() -> None:
    cursor = FeedbackListCursor(
        ingested_at=datetime(2026, 4, 23, 5, 0, tzinfo=UTC),
        id=UUID("00000000-0000-0000-0000-0000000000ab"),
    )

    encoded = encode_cursor(cursor)
    decoded = decode_cursor(encoded)

    assert decoded == cursor
