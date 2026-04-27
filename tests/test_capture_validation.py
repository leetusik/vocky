"""Validation tests for capture feedback normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vocky.capture import (
    CaptureFeedbackSourceInput,
    CaptureFeedbackValidationError,
    McpCaptureFeedbackInput,
    RestCaptureFeedbackInput,
    normalize_mcp_payload,
    normalize_rest_payload,
)


def make_input(**overrides: object) -> McpCaptureFeedbackInput:
    """Create a default raw capture input for tests."""

    data = {
        "message": "Helpful feedback",
        "source": CaptureFeedbackSourceInput(product="vocky-cli"),
        "feedback_value": None,
        "comment": None,
        "channel": None,
        "conversation_id": None,
        "session_id": None,
        "target_type": None,
        "target_id": None,
        "target_role": None,
        "target_text": None,
        "event_at": None,
        "tags": None,
        "messages": None,
        "used_context": None,
        "source_metadata": {},
        "attributes": {},
    }
    data.update(overrides)
    return McpCaptureFeedbackInput(**data)


def test_blank_message_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="message must not be blank"):
        normalize_mcp_payload(make_input(message="   "))


def test_blank_source_product_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="source.product must not be blank"):
        normalize_mcp_payload(make_input(source=CaptureFeedbackSourceInput(product="  ")))


def test_naive_event_at_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="event_at must include a timezone offset"):
        normalize_mcp_payload(make_input(event_at="2026-04-23T14:00:00"))


def test_blank_tag_is_rejected() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="tags must not contain blank values"):
        normalize_mcp_payload(make_input(tags=["valid", "   "]))


def test_duplicate_tags_are_rejected_after_normalization() -> None:
    with pytest.raises(CaptureFeedbackValidationError, match="tags must not contain duplicates"):
        normalize_mcp_payload(make_input(tags=["bug", " bug "]))


def test_invalid_feedback_value_is_rejected() -> None:
    with pytest.raises(
        CaptureFeedbackValidationError,
        match="feedback_value must be 1 for like or 2 for dislike",
    ):
        normalize_mcp_payload(make_input(feedback_value=3))


def test_invalid_target_type_is_rejected() -> None:
    with pytest.raises(
        CaptureFeedbackValidationError,
        match="target_type must be one of: message, conversation, surface",
    ):
        normalize_mcp_payload(make_input(target_type="answer"))


def test_invalid_target_role_is_rejected() -> None:
    with pytest.raises(
        CaptureFeedbackValidationError,
        match="target_role must be one of: user, assistant, system, tool",
    ):
        normalize_mcp_payload(make_input(target_role="bot"))


def test_action_feedback_context_is_accepted_and_event_at_is_normalized() -> None:
    normalized = normalize_mcp_payload(
        make_input(
            feedback_value=2,
            comment="  The answer ignored my billing context  ",
            channel=" web ",
            event_at="2026-04-23T14:00:00+09:00",
            tags=[" billing ", "bug"],
            messages=[
                {"role": "user", "content": "Why did export fail?"},
                {"role": "assistant", "content": "Try again later."},
            ],
            used_context=[{"source": "billing-doc", "snippet": "CSV export"}],
            source_metadata={"channel": "mcp"},
            attributes={"priority": "high"},
            conversation_id="  conv-123  ",
            session_id="   ",
            target_type=" message ",
            target_id=" msg-456 ",
            target_role=" assistant ",
            target_text="  Click export to download the CSV.  ",
        )
    )

    assert normalized.payload.tags == ("billing", "bug")
    assert normalized.payload.feedback_value == 2
    assert normalized.payload.comment == "The answer ignored my billing context"
    assert normalized.payload.channel == "web"
    assert normalized.payload.messages == (
        {"role": "user", "content": "Why did export fail?"},
        {"role": "assistant", "content": "Try again later."},
    )
    assert normalized.payload.used_context == (
        {"source": "billing-doc", "snippet": "CSV export"},
    )
    assert normalized.payload.source_metadata == {"channel": "mcp"}
    assert normalized.payload.attributes == {"priority": "high"}
    assert normalized.payload.conversation_id == "conv-123"
    assert normalized.payload.session_id is None
    assert normalized.payload.target_type == "message"
    assert normalized.payload.target_id == "msg-456"
    assert normalized.payload.target_role == "assistant"
    assert normalized.payload.target_text == "Click export to download the CSV."
    assert normalized.normalized_event_at == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)


def test_blank_target_fields_normalize_to_none() -> None:
    normalized = normalize_mcp_payload(
        make_input(
            target_type="   ",
            target_id=" ",
            target_role="\t",
            target_text="\n",
        )
    )

    assert normalized.payload.target_type is None
    assert normalized.payload.target_id is None
    assert normalized.payload.target_role is None
    assert normalized.payload.target_text is None


def test_rest_payload_uses_shared_capture_normalization() -> None:
    normalized = normalize_rest_payload(
        RestCaptureFeedbackInput(
            message="  Pricing page feedback  ",
            source=CaptureFeedbackSourceInput(product="product-site", integration="feedback-api"),
            target_type=" surface ",
            target_id=" pricing-page ",
            target_text="  Pricing page  ",
            source_metadata={"path": "/pricing"},
            attributes={"plan": "team"},
        )
    )

    assert normalized.payload.message == "Pricing page feedback"
    assert normalized.payload.source_product == "product-site"
    assert normalized.payload.source_integration == "feedback-api"
    assert normalized.payload.feedback_value is None
    assert normalized.payload.target_type == "surface"
    assert normalized.payload.target_id == "pricing-page"
    assert normalized.payload.target_text == "Pricing page"
    assert normalized.payload.source_metadata == {"path": "/pricing"}
    assert normalized.payload.attributes == {"plan": "team"}
