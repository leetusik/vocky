"""Validation tests for capture feedback normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vocky.tools.capture_feedback import (
    CaptureFeedbackInput,
    CaptureFeedbackSourceInput,
    CaptureFeedbackValidationError,
    normalize_payload,
)


def make_input(**overrides: object) -> CaptureFeedbackInput:
    """Create a default raw capture input for tests."""

    data = {
        "message": "Helpful feedback",
        "source": CaptureFeedbackSourceInput(product="vocky-cli"),
        "conversation_id": None,
        "session_id": None,
        "event_at": None,
        "tags": None,
        "source_metadata": {},
        "attributes": {},
    }
    data.update(overrides)
    return CaptureFeedbackInput(**data)


def test_blank_message_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="message must not be blank"):
        normalize_payload(make_input(message="   "))


def test_blank_source_product_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="source.product must not be blank"):
        normalize_payload(make_input(source=CaptureFeedbackSourceInput(product="  ")))


def test_naive_event_at_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="event_at must include a timezone offset"):
        normalize_payload(make_input(event_at="2026-04-23T14:00:00"))


def test_blank_tag_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="tags must not contain blank values"):
        normalize_payload(make_input(tags=["valid", "   "]))


def test_duplicate_tags_are_rejected_after_normalization() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="tags must not contain duplicates"):
        normalize_payload(make_input(tags=["bug", " bug "]))


def test_json_metadata_is_accepted_and_event_at_is_normalized() -> None:
    normalized = normalize_payload(
        make_input(
            event_at="2026-04-23T14:00:00+09:00",
            tags=[" billing ", "bug"],
            source_metadata={"channel": "mcp"},
            attributes={"priority": "high"},
            conversation_id="  conv-123  ",
            session_id="   ",
        )
    )

    assert normalized.payload.tags == ("billing", "bug")
    assert normalized.payload.source_metadata == {"channel": "mcp"}
    assert normalized.payload.attributes == {"priority": "high"}
    assert normalized.payload.conversation_id == "conv-123"
    assert normalized.payload.session_id is None
    assert normalized.normalized_event_at == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)
