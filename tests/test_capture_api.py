"""Public REST capture API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import fakeredis.aioredis
import httpx
import pytest
from starlette.applications import Starlette

from vocky.capture_queue import CaptureQueue, CaptureQueueError
import vocky.api as api_module
from vocky.api import routes as api_routes


def make_api_app() -> Starlette:
    """Create a test app with only public REST API routes."""

    return Starlette(routes=api_routes)


@pytest.mark.anyio
async def test_capture_feedback_accepts_message_action_payload_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "The export flow is broken",
                "source": {"product": "vocky-cli", "integration": "pytest"},
                "feedback_value": 2,
                "comment": "The answer did not fix export",
                "channel": "web",
                "user_id": "user_123",
                "trigger_type": "dislike",
                "trigger_message": "Thumbs down",
                "trigger_metadata": {"control_id": "assistant-message-1-downvote"},
                "target_type": "message",
                "target_id": "assistant-message-1",
                "target_role": "assistant",
                "target_text": "Click export",
                "event_at": "2026-04-23T14:00:00+09:00",
                "tags": ["billing", " bug "],
                "messages": [
                    {"role": "user", "content": "Export billing data"},
                    {"role": "assistant", "content": "Click export"},
                ],
                "used_context": [{"source": "billing-doc", "snippet": "Export steps"}],
                "source_metadata": {"channel": "pytest"},
                "attributes": {"priority": "high"},
            },
        )

    assert response.status_code == 202
    assert set(response.json()) == {"request_id", "accepted_at", "status"}
    assert response.json()["status"] == "accepted"
    assert await redis_client.llen("vocky:capture:feedback") == 1

    queued_job = await queue.pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.feedback_value == 2
    assert queued_job.payload.comment == "The answer did not fix export"
    assert queued_job.payload.channel == "web"
    assert queued_job.payload.user_id == "user_123"
    assert queued_job.payload.trigger_type == "dislike"
    assert queued_job.payload.trigger_message == "Thumbs down"
    assert queued_job.payload.trigger_metadata == {"control_id": "assistant-message-1-downvote"}
    assert queued_job.payload.target_type == "message"
    assert queued_job.payload.target_id == "assistant-message-1"
    assert queued_job.payload.target_role == "assistant"
    assert queued_job.payload.target_text == "Click export"
    assert queued_job.payload.event_at == datetime(2026, 4, 23, 5, 0, tzinfo=UTC)
    assert queued_job.payload.tags == ("billing", "bug")
    assert queued_job.payload.messages == (
        {"role": "user", "content": "Export billing data"},
        {"role": "assistant", "content": "Click export"},
    )
    assert queued_job.payload.used_context == (
        {"source": "billing-doc", "snippet": "Export steps"},
    )
    assert queued_job.payload.source_metadata == {"channel": "pytest"}
    assert queued_job.payload.attributes == {"priority": "high"}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_capture_feedback_accepts_surface_product_payload_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Pricing page feedback button was hard to find",
                "source": {"product": "marketing-site", "integration": "web-backend"},
                "comment": "I wanted to send feedback but did not notice the button",
                "channel": "web",
                "session_id": "sess_123",
                "user_id": "user_123",
                "trigger_type": "comment",
                "trigger_message": "Pricing feedback form",
                "trigger_metadata": {"form_id": "pricing-feedback"},
                "target_type": "surface",
                "target_id": "pricing-page-feedback-button",
                "target_text": "Feedback",
                "tags": ["website", "pricing"],
                "source_metadata": {"path": "/pricing", "referrer": "/"},
                "attributes": {"plan": "team", "locale": "en-US"},
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert await redis_client.llen("vocky:capture:feedback") == 1

    queued_job = await queue.pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.message == "Pricing page feedback button was hard to find"
    assert queued_job.payload.source_product == "marketing-site"
    assert queued_job.payload.source_integration == "web-backend"
    assert queued_job.payload.feedback_value is None
    assert queued_job.payload.comment == "I wanted to send feedback but did not notice the button"
    assert queued_job.payload.channel == "web"
    assert queued_job.payload.conversation_id is None
    assert queued_job.payload.session_id == "sess_123"
    assert queued_job.payload.user_id == "user_123"
    assert queued_job.payload.trigger_type == "comment"
    assert queued_job.payload.trigger_message == "Pricing feedback form"
    assert queued_job.payload.trigger_metadata == {"form_id": "pricing-feedback"}
    assert queued_job.payload.target_type == "surface"
    assert queued_job.payload.target_id == "pricing-page-feedback-button"
    assert queued_job.payload.target_role is None
    assert queued_job.payload.target_text == "Feedback"
    assert queued_job.payload.tags == ("website", "pricing")
    assert queued_job.payload.messages == ()
    assert queued_job.payload.used_context == ()
    assert queued_job.payload.source_metadata == {"path": "/pricing", "referrer": "/"}
    assert queued_job.payload.attributes == {"plan": "team", "locale": "en-US"}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_capture_feedback_validation_error_returns_400() -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "   ",
                "source": {"product": "vocky-cli"},
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "message must not be blank"}


@pytest.mark.anyio
async def test_capture_feedback_invalid_channel_returns_400() -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Invalid channel",
                "source": {"product": "vocky-cli"},
                "channel": "email",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "channel must be one of: web, mobile, support"}


@pytest.mark.anyio
async def test_capture_feedback_invalid_trigger_type_returns_400() -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Invalid trigger",
                "source": {"product": "vocky-cli"},
                "trigger_type": "thumbs-up",
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "trigger_type must be one of: like, dislike, comment, rating, survey, manual, other"
    }


@pytest.mark.anyio
async def test_capture_feedback_invalid_trigger_metadata_returns_400() -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Invalid trigger metadata",
                "source": {"product": "vocky-cli"},
                "trigger_metadata": ["not", "object"],
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "trigger_metadata must be a JSON object"}


@pytest.mark.anyio
async def test_capture_feedback_blank_channel_enqueues_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Blank channel",
                "source": {"product": "vocky-cli"},
                "channel": "   ",
                "user_id": " ",
                "trigger_type": " ",
                "trigger_message": "\t",
            },
        )

    assert response.status_code == 202
    queued_job = await queue.pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.channel is None
    assert queued_job.payload.user_id is None
    assert queued_job.payload.trigger_type is None
    assert queued_job.payload.trigger_message is None
    assert queued_job.payload.trigger_metadata == {}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_capture_feedback_omitted_target_type_remains_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Legacy product feedback without target type",
                "source": {"product": "marketing-site", "integration": "legacy-webhook"},
                "comment": "The page was confusing",
                "source_metadata": {"path": "/pricing"},
            },
        )

    assert response.status_code == 202
    queued_job = await queue.pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.target_type is None
    assert queued_job.payload.target_id is None
    assert queued_job.payload.target_role is None
    assert queued_job.payload.target_text is None
    assert queued_job.payload.user_id is None
    assert queued_job.payload.trigger_type is None
    assert queued_job.payload.trigger_message is None
    assert queued_job.payload.trigger_metadata == {}
    assert queued_job.payload.source_metadata == {"path": "/pricing"}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_capture_feedback_body_shape_errors_return_400() -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        malformed_response = await client.post(
            "/api/feedback",
            content="{",
            headers={"content-type": "application/json"},
        )
        array_response = await client.post("/api/feedback", json=[])
        missing_field_response = await client.post(
            "/api/feedback",
            json={"message": "Missing source product", "source": {}},
        )

    assert malformed_response.status_code == 400
    assert malformed_response.json() == {"detail": "request body must be valid JSON"}
    assert array_response.status_code == 400
    assert array_response.json() == {"detail": "request body must be a JSON object"}
    assert missing_field_response.status_code == 400
    assert missing_field_response.json() == {"detail": "source.product: Field required"}


@pytest.mark.anyio
async def test_capture_feedback_queue_failure_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenQueue:
        async def enqueue_feedback(self, payload):
            raise CaptureQueueError("boom")

    monkeypatch.setattr(api_module, "get_capture_queue", lambda: BrokenQueue())

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "message": "Queue failure",
                "source": {"product": "vocky-cli"},
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "capture queue unavailable"}
