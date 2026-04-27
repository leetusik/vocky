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
async def test_capture_feedback_accepts_payload_and_enqueues(
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
