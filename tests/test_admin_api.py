"""Admin REST API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

import vocky.admin_api as admin_api_module
from vocky.admin_api import routes as admin_routes
from vocky.db import get_engine
from vocky.storage import LocalFilesystemAttachmentStorage, StorageObjectNotFoundError


def make_admin_app() -> Starlette:
    """Create a test app with only Admin REST routes."""

    return Starlette(routes=admin_routes)


@pytest.fixture
def admin_attachment_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalFilesystemAttachmentStorage:
    """Point the admin attachment routes at a temp-dir storage backend."""

    storage = LocalFilesystemAttachmentStorage(tmp_path)
    monkeypatch.setattr(
        "vocky.admin_api.get_attachment_storage", lambda: storage
    )
    return storage


async def _seed_feedback_row(*, feedback_id: str, source_product: str = "changple5") -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events (id, message, source_product) "
                "VALUES (:id, :message, :source_product)"
            ),
            {"id": feedback_id, "message": "with attachment", "source_product": source_product},
        )


async def _seed_attachment_row(
    *,
    attachment_id: str,
    feedback_id: str | None,
    storage_key: str,
    created_at: datetime,
    content_type: str = "image/png",
    byte_size: int = 3,
    filename: str | None = None,
    claimed_source_product: str = "changple5",
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_attachments ("
                "id, feedback_id, storage_key, content_type, byte_size, filename, "
                "claimed_user_id, claimed_source_product, created_at"
                ") VALUES ("
                ":id, :feedback_id, :storage_key, :content_type, :byte_size, :filename, "
                "NULL, :claimed_source_product, :created_at)"
            ),
            {
                "id": attachment_id,
                "feedback_id": feedback_id,
                "storage_key": storage_key,
                "content_type": content_type,
                "byte_size": byte_size,
                "filename": filename,
                "claimed_source_product": claimed_source_product,
                "created_at": created_at,
            },
        )


@pytest.mark.anyio
async def test_admin_list_feedback_returns_likes_and_dislikes(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, source_integration, conversation_id, "
                "session_id, user_id, trigger_type, trigger_message, trigger_metadata, "
                "target_type, target_id, target_role, target_text, "
                "feedback_value, comment, channel, event_at, ingested_at, "
                "tags, messages, used_context, source_metadata, attributes"
                ") VALUES "
                "(:like_id, :like_message, :product, :integration, :conversation_id, "
                ":session_id, :like_user_id, :like_trigger_type, :like_trigger_message, "
                "CAST(:like_trigger_metadata AS jsonb), "
                ":target_type, :target_id, :target_role, :target_text, "
                "1, :like_comment, :channel, :event_at, :like_ingested_at, "
                ":tags, CAST(:like_messages AS jsonb), CAST(:like_context AS jsonb), "
                "CAST(:metadata AS jsonb), CAST(:like_attributes AS jsonb)), "
                "(:dislike_id, :dislike_message, :product, :integration, :conversation_id, "
                ":session_id, :dislike_user_id, :dislike_trigger_type, "
                ":dislike_trigger_message, CAST(:dislike_trigger_metadata AS jsonb), "
                "NULL, NULL, NULL, NULL, "
                "2, :dislike_comment, :channel, :event_at, :dislike_ingested_at, "
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
                "like_user_id": "user-admin",
                "like_trigger_type": "like",
                "like_trigger_message": "Thumbs up",
                "like_trigger_metadata": "{\"control_id\": \"admin-like\"}",
                "dislike_user_id": "user-admin",
                "dislike_trigger_type": "dislike",
                "dislike_trigger_message": "Thumbs down",
                "dislike_trigger_metadata": "{\"control_id\": \"admin-dislike\"}",
                "target_type": "message",
                "target_id": "assistant-admin",
                "target_role": "assistant",
                "target_text": "Good answer",
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
                "user_id": "user-admin",
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
        target_type_response = await client.get(
            "/admin/api/feedback",
            params={
                "source_product": "admin-product",
                "target_type": " message ",
            },
        )
        trigger_type_response = await client.get(
            "/admin/api/feedback",
            params={
                "source_product": "admin-product",
                "trigger_type": " like ",
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
    assert records[0]["user_id"] == "user-admin"
    assert records[0]["trigger_type"] == "dislike"
    assert records[0]["trigger_message"] == "Thumbs down"
    assert records[0]["trigger_metadata"] == {"control_id": "admin-dislike"}
    assert records[0]["target_type"] is None
    assert records[0]["target_id"] is None
    assert records[0]["target_role"] is None
    assert records[0]["target_text"] is None
    assert records[0]["messages"] == [{"role": "assistant", "content": "bad"}]
    assert records[0]["used_context"] == [{"source": "doc", "snippet": "bad"}]
    assert records[1]["target_type"] == "message"
    assert records[1]["target_id"] == "assistant-admin"
    assert records[1]["target_role"] == "assistant"
    assert records[1]["target_text"] == "Good answer"

    assert dislike_response.status_code == 200
    assert [record["message"] for record in dislike_response.json()["records"]] == [
        "disliked answer"
    ]
    assert target_type_response.status_code == 200
    assert [record["message"] for record in target_type_response.json()["records"]] == [
        "liked answer"
    ]
    assert trigger_type_response.status_code == 200
    assert [record["message"] for record in trigger_type_response.json()["records"]] == [
        "liked answer"
    ]


@pytest.mark.anyio
async def test_admin_feedback_metrics_returns_totals_and_daily_counts(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, feedback_value, ingested_at"
                ") VALUES "
                "(:liked_id, :liked_message, :product, 1, :liked_ingested_at), "
                "(:disliked_id, :disliked_message, :product, 2, :disliked_ingested_at), "
                "(:unrated_id, :unrated_message, :product, NULL, :unrated_ingested_at), "
                "(:excluded_id, :excluded_message, :product, 1, :excluded_ingested_at)"
            ),
            {
                "liked_id": "00000000-0000-0000-0000-0000000000b1",
                "liked_message": "liked metric",
                "disliked_id": "00000000-0000-0000-0000-0000000000b2",
                "disliked_message": "disliked metric",
                "unrated_id": "00000000-0000-0000-0000-0000000000b3",
                "unrated_message": "unrated metric",
                "excluded_id": "00000000-0000-0000-0000-0000000000b4",
                "excluded_message": "excluded metric",
                "product": "admin-product",
                "liked_ingested_at": datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
                "disliked_ingested_at": datetime(2026, 4, 25, 1, 0, tzinfo=UTC),
                "unrated_ingested_at": datetime(2026, 4, 25, 2, 0, tzinfo=UTC),
                "excluded_ingested_at": datetime(2026, 4, 27, 0, 0, tzinfo=UTC),
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/api/feedback/metrics",
            params={
                "start_ingested_at": "2026-04-23T09:00:00+09:00",
                "end_ingested_at": "2026-04-27T09:00:00+09:00",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "window": {
            "start_ingested_at": "2026-04-23T00:00:00Z",
            "end_ingested_at": "2026-04-27T00:00:00Z",
        },
        "totals": {
            "total": 3,
            "liked": 1,
            "disliked": 1,
            "unrated": 1,
        },
        "daily_counts": [
            {
                "day": "2026-04-23",
                "total": 1,
                "liked": 1,
                "disliked": 0,
                "unrated": 0,
            },
            {
                "day": "2026-04-24",
                "total": 0,
                "liked": 0,
                "disliked": 0,
                "unrated": 0,
            },
            {
                "day": "2026-04-25",
                "total": 2,
                "liked": 0,
                "disliked": 1,
                "unrated": 1,
            },
            {
                "day": "2026-04-26",
                "total": 0,
                "liked": 0,
                "disliked": 0,
                "unrated": 0,
            },
        ],
    }


@pytest.mark.anyio
async def test_admin_feedback_metrics_validation_errors(configured_database: str) -> None:
    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing_start_response = await client.get(
            "/admin/api/feedback/metrics",
            params={"end_ingested_at": "2026-04-24T00:00:00Z"},
        )
        missing_end_response = await client.get(
            "/admin/api/feedback/metrics",
            params={"start_ingested_at": "2026-04-24T00:00:00Z"},
        )
        naive_response = await client.get(
            "/admin/api/feedback/metrics",
            params={
                "start_ingested_at": "2026-04-24T00:00:00",
                "end_ingested_at": "2026-04-25T00:00:00Z",
            },
        )
        invalid_window_response = await client.get(
            "/admin/api/feedback/metrics",
            params={
                "start_ingested_at": "2026-04-25T00:00:00Z",
                "end_ingested_at": "2026-04-24T00:00:00Z",
            },
        )

    assert missing_start_response.status_code == 400
    assert missing_start_response.json() == {"detail": "start_ingested_at is required"}
    assert missing_end_response.status_code == 400
    assert missing_end_response.json() == {"detail": "end_ingested_at is required"}
    assert naive_response.status_code == 400
    assert naive_response.json() == {
        "detail": "start_ingested_at must include a timezone offset"
    }
    assert invalid_window_response.status_code == 400
    assert invalid_window_response.json() == {
        "detail": "start_ingested_at must be before end_ingested_at"
    }


@pytest.mark.anyio
async def test_admin_feedback_metrics_storage_failure_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenService:
        async def get_feedback_metrics(self, query):
            raise admin_api_module.FeedbackReadError("boom")

    monkeypatch.setattr(admin_api_module, "get_feedback_service", lambda: BrokenService())

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/api/feedback/metrics",
            params={
                "start_ingested_at": "2026-04-23T00:00:00Z",
                "end_ingested_at": "2026-04-24T00:00:00Z",
            },
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "storage read failed"}


@pytest.mark.anyio
async def test_admin_get_feedback_returns_full_record(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-000000000081"
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, feedback_value, comment, channel, "
                "user_id, trigger_type, trigger_message, trigger_metadata, "
                "target_type, target_id, target_role, target_text, ingested_at, "
                "messages, used_context"
                ") VALUES ("
                ":id, :message, :source_product, 1, :comment, :channel, "
                ":user_id, :trigger_type, :trigger_message, CAST(:trigger_metadata AS jsonb), "
                ":target_type, :target_id, :target_role, :target_text, :ingested_at, "
                "CAST(:messages AS jsonb), CAST(:used_context AS jsonb)"
                ")"
            ),
            {
                "id": feedback_id,
                "message": "detail answer",
                "source_product": "admin-product",
                "comment": "detail comment",
                "channel": "web",
                "user_id": "user-detail",
                "trigger_type": "manual",
                "trigger_message": "Operator import",
                "trigger_metadata": "{\"source\": \"operator\"}",
                "target_type": "message",
                "target_id": "assistant-detail",
                "target_role": "assistant",
                "target_text": "Detailed answer",
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
    assert response.json()["record"]["user_id"] == "user-detail"
    assert response.json()["record"]["trigger_type"] == "manual"
    assert response.json()["record"]["trigger_message"] == "Operator import"
    assert response.json()["record"]["trigger_metadata"] == {"source": "operator"}
    assert response.json()["record"]["target_type"] == "message"
    assert response.json()["record"]["target_id"] == "assistant-detail"
    assert response.json()["record"]["target_role"] == "assistant"
    assert response.json()["record"]["target_text"] == "Detailed answer"
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
        clear_channel_response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={"channel": "   "},
        )
        invalid_channel_response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={"channel": "email"},
        )
        empty_response = await client.patch(f"/admin/api/feedback/{feedback_id}", json={})
        invalid_response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={"feedback_value": 4},
        )
        target_only_response = await client.patch(
            f"/admin/api/feedback/{feedback_id}",
            json={"target_text": "new target text"},
        )

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["feedback_value"] == 1
    assert record["comment"] == "updated comment"
    assert record["channel"] == "support"
    assert record["tags"] == ["reviewed", "liked"]
    assert record["source_metadata"] == {"source": "admin"}
    assert record["attributes"] == {"reviewed": True}

    assert clear_channel_response.status_code == 200
    assert clear_channel_response.json()["record"]["channel"] is None
    assert invalid_channel_response.status_code == 400
    assert invalid_channel_response.json() == {
        "detail": "channel must be one of: web, mobile, support"
    }

    assert empty_response.status_code == 400
    assert empty_response.json() == {
        "detail": "request body must include at least one editable field"
    }
    assert invalid_response.status_code == 400
    assert invalid_response.json() == {
        "detail": "feedback_value must be 1 for like or 2 for dislike"
    }
    assert target_only_response.status_code == 400
    assert target_only_response.json() == {
        "detail": "request body must include at least one editable field"
    }


@pytest.mark.anyio
async def test_admin_list_feedback_preserves_legacy_channel_filter(
    configured_database: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, channel, ingested_at"
                ") VALUES ("
                ":id, :message, :source_product, :channel, :ingested_at"
                ")"
            ),
            {
                "id": "00000000-0000-0000-0000-000000000092",
                "message": "legacy channel row",
                "source_product": "admin-product",
                "channel": "email",
                "ingested_at": datetime(2026, 4, 24, 5, 0, tzinfo=UTC),
            },
        )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/admin/api/feedback",
            params={"channel": " email "},
        )

    assert response.status_code == 200
    assert response.json()["records"] == [
        {
            "id": "00000000-0000-0000-0000-000000000092",
            "message": "legacy channel row",
            "source_product": "admin-product",
            "feedback_value": None,
            "comment": None,
            "channel": "email",
            "source_integration": None,
            "conversation_id": None,
            "session_id": None,
            "user_id": None,
            "trigger_type": None,
            "trigger_message": None,
            "trigger_metadata": {},
            "target_type": None,
            "target_id": None,
            "target_role": None,
            "target_text": None,
            "event_at": None,
            "ingested_at": "2026-04-24T05:00:00Z",
            "tags": [],
            "messages": [],
            "used_context": [],
            "source_metadata": {},
            "attributes": {},
        }
    ]


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
        invalid_target_type_response = await client.get(
            "/admin/api/feedback",
            params={"target_type": "answer"},
        )
        invalid_trigger_type_response = await client.get(
            "/admin/api/feedback",
            params={"trigger_type": "reaction"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "feedback_value must be 1 for like or 2 for dislike"
    }
    assert invalid_target_type_response.status_code == 400
    assert invalid_target_type_response.json() == {
        "detail": "target_type must be one of: message, conversation, surface"
    }
    assert invalid_trigger_type_response.status_code == 400
    assert invalid_trigger_type_response.json() == {
        "detail": "trigger_type must be one of: like, dislike, comment, rating, survey, manual, other"
    }


async def _seed_feedback(feedback_id: str, *, message: str = "feedback row") -> None:
    """Insert a minimal feedback row for comment tests."""

    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events (id, message, source_product) "
                "VALUES (:id, :message, :source_product)"
            ),
            {"id": feedback_id, "message": message, "source_product": "admin-product"},
        )


@pytest.mark.anyio
async def test_admin_add_and_list_feedback_comments(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c1"
    await _seed_feedback(feedback_id)

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            f"/admin/api/feedback/{feedback_id}/comments",
            json={"author": "  ops-jane  ", "body": "  Escalated to billing  "},
        )
        second = await client.post(
            f"/admin/api/feedback/{feedback_id}/comments",
            json={"body": "Awaiting customer reply"},
        )
        list_response = await client.get(f"/admin/api/feedback/{feedback_id}/comments")

    assert first.status_code == 201
    first_comment = first.json()["comment"]
    assert first_comment["author"] == "ops-jane"
    assert first_comment["body"] == "Escalated to billing"
    assert first_comment["id"]
    assert first_comment["created_at"].endswith("Z")

    assert second.status_code == 201
    assert second.json()["comment"]["author"] is None

    assert list_response.status_code == 200
    comments = list_response.json()["comments"]
    assert [comment["body"] for comment in comments] == [
        "Escalated to billing",
        "Awaiting customer reply",
    ]
    assert [comment["author"] for comment in comments] == ["ops-jane", None]


@pytest.mark.anyio
async def test_admin_post_comment_blank_body_returns_400(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c2"
    await _seed_feedback(feedback_id)

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        blank_response = await client.post(
            f"/admin/api/feedback/{feedback_id}/comments",
            json={"body": "   "},
        )
        list_response = await client.get(f"/admin/api/feedback/{feedback_id}/comments")

    assert blank_response.status_code == 400
    assert blank_response.json() == {"detail": "body must not be blank"}
    assert list_response.status_code == 200
    assert list_response.json() == {"comments": []}


@pytest.mark.anyio
async def test_admin_comment_endpoints_missing_parent_returns_404(
    configured_database: str,
) -> None:
    missing_id = "00000000-0000-0000-0000-0000000000ff"

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_response = await client.post(
            f"/admin/api/feedback/{missing_id}/comments",
            json={"body": "no parent"},
        )
        get_response = await client.get(f"/admin/api/feedback/{missing_id}/comments")

    assert post_response.status_code == 404
    assert post_response.json() == {"detail": "feedback not found"}
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "feedback not found"}


@pytest.mark.anyio
async def test_admin_get_feedback_detail_includes_comments(
    configured_database: str,
) -> None:
    with_comment_id = "00000000-0000-0000-0000-0000000000c3"
    without_comment_id = "00000000-0000-0000-0000-0000000000c4"
    await _seed_feedback(with_comment_id, message="has comments")
    await _seed_feedback(without_comment_id, message="no comments")

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            f"/admin/api/feedback/{with_comment_id}/comments",
            json={"author": "ops-amy", "body": "Reviewed and resolved"},
        )
        with_comment = await client.get(f"/admin/api/feedback/{with_comment_id}")
        without_comment = await client.get(f"/admin/api/feedback/{without_comment_id}")

    assert with_comment.status_code == 200
    record = with_comment.json()["record"]
    assert record["id"] == with_comment_id
    assert len(record["comments"]) == 1
    assert record["comments"][0]["author"] == "ops-amy"
    assert record["comments"][0]["body"] == "Reviewed and resolved"

    assert without_comment.status_code == 200
    assert without_comment.json()["record"]["comments"] == []


@pytest.mark.anyio
async def test_admin_detail_includes_attachments(configured_database: str) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000d1"
    first = "00000000-0000-0000-0000-0000000000d2"
    second = "00000000-0000-0000-0000-0000000000d3"
    await _seed_feedback_row(feedback_id=feedback_id)
    await _seed_attachment_row(
        attachment_id=second,
        feedback_id=feedback_id,
        storage_key="key-second",
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
        filename="second.png",
    )
    await _seed_attachment_row(
        attachment_id=first,
        feedback_id=feedback_id,
        storage_key="key-first",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        filename="first.png",
    )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/admin/api/feedback/{feedback_id}")

    assert response.status_code == 200
    attachments = response.json()["record"]["attachments"]
    assert [item["id"] for item in attachments] == [first, second]
    assert attachments[0]["content_type"] == "image/png"
    assert attachments[0]["filename"] == "first.png"
    assert attachments[0]["byte_size"] == 3
    assert (
        attachments[0]["url"]
        == f"/admin/api/feedback/{feedback_id}/attachments/{first}"
    )


@pytest.mark.anyio
async def test_admin_attachment_download_returns_bytes(
    configured_database: str,
    admin_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000e1"
    attachment_id = "00000000-0000-0000-0000-0000000000e2"
    payload = b"\x89PNG\r\n\x1a\nadmin-bytes"
    await _seed_feedback_row(feedback_id=feedback_id)
    await _seed_attachment_row(
        attachment_id=attachment_id,
        feedback_id=feedback_id,
        storage_key="admin-key",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
    )
    admin_attachment_storage.save("admin-key", payload)

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/admin/api/feedback/{feedback_id}/attachments/{attachment_id}"
        )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"].startswith("image/png")


@pytest.mark.anyio
async def test_admin_attachment_download_wrong_feedback_returns_404(
    configured_database: str,
    admin_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_a = "00000000-0000-0000-0000-0000000000f1"
    feedback_b = "00000000-0000-0000-0000-0000000000f2"
    attachment_id = "00000000-0000-0000-0000-0000000000f3"
    await _seed_feedback_row(feedback_id=feedback_a)
    await _seed_feedback_row(feedback_id=feedback_b)
    await _seed_attachment_row(
        attachment_id=attachment_id,
        feedback_id=feedback_a,
        storage_key="key-a",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
    )

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/admin/api/feedback/{feedback_b}/attachments/{attachment_id}"
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_admin_delete_removes_attachment_files(
    configured_database: str,
    admin_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000fa"
    attachment_id = "00000000-0000-0000-0000-0000000000fb"
    await _seed_feedback_row(feedback_id=feedback_id)
    await _seed_attachment_row(
        attachment_id=attachment_id,
        feedback_id=feedback_id,
        storage_key="delete-key",
        created_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
    )
    admin_attachment_storage.save("delete-key", b"bytes-to-remove")

    transport = httpx.ASGITransport(app=make_admin_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.delete(f"/admin/api/feedback/{feedback_id}")

    assert response.status_code == 204
    with pytest.raises(StorageObjectNotFoundError):
        admin_attachment_storage.load("delete-key")
