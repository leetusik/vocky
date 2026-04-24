"""Admin REST API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

from vocky.admin_api import routes as admin_routes
from vocky.db import get_engine


def make_admin_app() -> Starlette:
    """Create a test app with only Admin REST routes."""

    return Starlette(routes=admin_routes)


@pytest.mark.anyio
async def test_admin_list_feedback_returns_likes_and_dislikes(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, feedback_value, comment, channel, event_at, ingested_at, "
                "tags, messages, used_context, source_metadata, attributes"
                ") VALUES "
                "(:like_id, :like_message, :product, :integration, :conversation_id, "
                ":session_id, 1, :like_comment, :channel, :event_at, :like_ingested_at, "
                ":tags, CAST(:like_messages AS jsonb), CAST(:like_context AS jsonb), "
                "CAST(:metadata AS jsonb), CAST(:like_attributes AS jsonb)), "
                "(:dislike_id, :dislike_message, :product, :integration, :conversation_id, "
                ":session_id, 2, :dislike_comment, :channel, :event_at, :dislike_ingested_at, "
                ":tags, CAST(:dislike_messages AS jsonb), CAST(:dislike_context AS jsonb), "
                "CAST(:metadata AS jsonb), CAST(:dislike_attributes AS jsonb))"
            ),
            {
                "like_id": "00000000-0000-0000-0000-000000000071",
                "like_message": "liked answer",
                "dislike_id": "00000000-0000-0000-0000-000000000072",
                "dislike_message": "disliked answer",
                "product": "admin-product",
                "integration": "pytest",
                "conversation_id": "conv-admin",
                "session_id": "sess-admin",
                "like_comment": "good answer",
                "dislike_comment": "bad answer",
                "channel": "web",
                "event_at": datetime(2026, 4, 24, 2, 0, tzinfo=UTC),
                "like_ingested_at": datetime(2026, 4, 24, 2, 1, tzinfo=UTC),
                "dislike_ingested_at": datetime(2026, 4, 24, 2, 2, tzinfo=UTC),
                "tags": ["admin"],
                "like_messages": "[{\"role\": \"assistant\", \"content\": \"good\"}]",
                "dislike_messages": "[{\"role\": \"assistant\", \"content\": \"bad\"}]",
                "like_context": "[{\"source\": \"doc\", \"snippet\": \"good\"}]",
                "dislike_context": "[{\"source\": \"doc\", \"snippet\": \"bad\"}]",
                "metadata": "{\"channel\": \"web\"}",
                "like_attributes": "{\"reviewed\": false}",
                "dislike_attributes": "{\"severity\": \"high\"}",
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/api/feedback",
            params={
                "source_product": "admin-product",
                "channel": "web",
                "tag": "admin",
            },
        )
        dislike_response = await client.get(
            "/admin/api/feedback",
            params={
                "source_product": "admin-product",
                "feedback_value": "2",
            },
        )

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["message"] for record in records] == [
        "disliked answer",
        "liked answer",
    ]
    assert [record["feedback_value"] for record in records] == [2, 1]
    assert records[0]["comment"] == "bad answer"
    assert records[0]["messages"] == [{"role": "assistant", "content": "bad"}]
    assert records[0]["used_context"] == [{"source": "doc", "snippet": "bad"}]

    assert dislike_response.status_code == 200
    assert [record["message"] for record in dislike_response.json()["records"]] == [
        "disliked answer"
    ]


@pytest.mark.anyio
async def test_admin_get_feedback_returns_full_record(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-000000000081"
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, feedback_value, comment, channel, "
                "ingested_at, messages, used_context"
                ") VALUES ("
                ":id, :message, :source_product, 1, :comment, :channel, :ingested_at, "
                "CAST(:messages AS jsonb), CAST(:used_context AS jsonb)"
                ")"
            ),
            {
                "id": feedback_id,
                "message": "detail answer",
                "source_product": "admin-product",
                "comment": "detail comment",
                "channel": "web",
                "ingested_at": datetime(2026, 4, 24, 3, 0, tzinfo=UTC),
                "messages": "[{\"role\": \"assistant\", \"content\": \"detail\"}]",
                "used_context": "[{\"source\": \"doc\"}]",
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/admin/api/feedback/{feedback_id}")
        missing_response = await client.get(
            "/admin/api/feedback/00000000-0000-0000-0000-000000000099"
        )
        invalid_response = await client.get("/admin/api/feedback/not-a-uuid")

    assert response.status_code == 200
    assert response.json()["record"]["message"] == "detail answer"
    assert response.json()["record"]["messages"] == [
        {"role": "assistant", "content": "detail"}
    ]
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "feedback not found"}
    assert invalid_response.status_code == 400
    assert invalid_response.json() == {"detail": "feedback_id must be a valid UUID"}


@pytest.mark.anyio
async def test_admin_patch_feedback_updates_review_fields(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-000000000091"
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, feedback_value, comment, channel, "
                "ingested_at, tags, source_metadata, attributes"
                ") VALUES ("
                ":id, :message, :source_product, 2, :comment, :channel, :ingested_at, "
                ":tags, CAST(:source_metadata AS jsonb), CAST(:attributes AS jsonb)"
                ")"
            ),
            {
                "id": feedback_id,
                "message": "patch me",
                "source_product": "admin-product",
                "comment": "old comment",
                "channel": "web",
                "ingested_at": datetime(2026, 4, 24, 4, 0, tzinfo=UTC),
                "tags": ["old"],
                "source_metadata": "{\"old\": true}",
                "attributes": "{\"reviewed\": false}",
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={
                "feedback_value": 1,
                "comment": " updated comment ",
                "channel": " support ",
                "tags": ["reviewed", "liked"],
                "source_metadata": {"source": "admin"},
                "attributes": {"reviewed": True},
            },
        )
        empty_response = await client.patch(f"/admin/api/feedback/{feedback_id}", json={})
        invalid_response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={"feedback_value": 4},
        )

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["feedback_value"] == 1
    assert record["comment"] == "updated comment"
    assert record["channel"] == "support"
    assert record["tags"] == ["reviewed", "liked"]
    assert record["source_metadata"] == {"source": "admin"}
    assert record["attributes"] == {"reviewed": True}

    assert empty_response.status_code == 400
    assert empty_response.json() == {
        "detail": "request body must include at least one editable field"
    }
    assert invalid_response.status_code == 400
    assert invalid_response.json() == {
        "detail": "feedback_value must be 1 for like or 2 for dislike"
    }


@pytest.mark.anyio
async def test_admin_delete_feedback_removes_record(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000a1"
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events (id, message, source_product) "
                "VALUES (:id, :message, :source_product)"
            ),
            {
                "id": feedback_id,
                "message": "delete me",
                "source_product": "admin-product",
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        delete_response = await client.delete(f"/admin/api/feedback/{feedback_id}")
        get_response = await client.get(f"/admin/api/feedback/{feedback_id}")
        second_delete_response = await client.delete(f"/admin/api/feedback/{feedback_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404
    assert second_delete_response.status_code == 404


@pytest.mark.anyio
async def test_admin_list_feedback_validation_errors(configured_database: str) -> None:
    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/api/feedback",
            params={"feedback_value": "5"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "feedback_value must be 1 for like or 2 for dislike"
    }
