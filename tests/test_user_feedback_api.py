"""End-user feedback read REST tests (`GET /api/feedback`)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

from vocky.api import routes as api_routes
from vocky.auth import APIBearerAuthMiddleware
from vocky.db import get_engine
from vocky.storage import LocalFilesystemAttachmentStorage


def make_api_app(*, token: str = "") -> Starlette:
    """Create a test app with the public API routes and optional bearer auth."""

    app = Starlette(routes=api_routes)
    if token:
        app.add_middleware(APIBearerAuthMiddleware, token=token)
    return app


@pytest.fixture
def api_attachment_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalFilesystemAttachmentStorage:
    """Point the end-user download route at a temp-dir storage backend."""

    storage = LocalFilesystemAttachmentStorage(tmp_path)
    monkeypatch.setattr("vocky.api.get_attachment_storage", lambda: storage)
    return storage


async def _seed_attachment(
    *,
    attachment_id: str,
    feedback_id: str,
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


async def _seed_feedback(
    *,
    feedback_id: str,
    user_id: str,
    source_product: str,
    ingested_at: datetime,
    feedback_value: int | None = None,
    comment: str | None = None,
    message: str = "feedback row",
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, user_id, feedback_value, comment, ingested_at"
                ") VALUES ("
                ":id, :message, :source_product, :user_id, :feedback_value, :comment, :ingested_at"
                ")"
            ),
            {
                "id": feedback_id,
                "message": message,
                "source_product": source_product,
                "user_id": user_id,
                "feedback_value": feedback_value,
                "comment": comment,
                "ingested_at": ingested_at,
            },
        )


async def _seed_comment(
    *,
    feedback_id: str,
    body: str,
    created_at: datetime,
    author: str | None = None,
) -> None:
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


@pytest.mark.anyio
async def test_user_feedback_returns_only_caller_scope_with_comments(
    configured_database: str,
) -> None:
    mine = "00000000-0000-0000-0000-0000000000a1"
    other_user = "00000000-0000-0000-0000-0000000000a2"
    other_product = "00000000-0000-0000-0000-0000000000a3"

    await _seed_feedback(
        feedback_id=mine,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        feedback_value=1,
        comment="my own comment",
        message="mine",
    )
    await _seed_feedback(
        feedback_id=other_user,
        user_id="user-2",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        message="other user",
    )
    await _seed_feedback(
        feedback_id=other_product,
        user_id="user-1",
        source_product="other-product",
        ingested_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        message="other product",
    )
    await _seed_comment(
        feedback_id=mine,
        body="operator follow-up",
        created_at=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
        author="ops-jane",
    )

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/feedback",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["id"] for record in records] == [mine]
    record = records[0]
    assert record["message"] == "mine"
    assert record["user_id"] == "user-1"
    assert record["source_product"] == "changple5"
    assert record["feedback_value"] == 1
    assert record["comment"] == "my own comment"
    # Full record shape is echoed back, including operator-review/internal fields.
    assert record["channel"] is None
    assert record["tags"] == []
    assert record["attributes"] == {}
    # Operator comments are nested oldest-first.
    assert len(record["comments"]) == 1
    assert record["comments"][0]["author"] == "ops-jane"
    assert record["comments"][0]["body"] == "operator follow-up"


@pytest.mark.anyio
async def test_user_feedback_requires_user_id_and_source_product(
    configured_database: str,
) -> None:
    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing_user = await client.get(
            "/api/feedback", params={"source_product": "changple5"}
        )
        missing_product = await client.get(
            "/api/feedback", params={"user_id": "user-1"}
        )
        blank_user = await client.get(
            "/api/feedback", params={"user_id": "   ", "source_product": "changple5"}
        )
        blank_product = await client.get(
            "/api/feedback", params={"user_id": "user-1", "source_product": ""}
        )

    assert missing_user.status_code == 400
    assert missing_user.json() == {"detail": "user_id is required"}
    assert missing_product.status_code == 400
    assert missing_product.json() == {"detail": "source_product is required"}
    assert blank_user.status_code == 400
    assert blank_user.json() == {"detail": "user_id must not be blank"}
    assert blank_product.status_code == 400
    assert blank_product.json() == {"detail": "source_product must not be blank"}


@pytest.mark.anyio
async def test_user_feedback_basic_filter_narrows(configured_database: str) -> None:
    like_id = "00000000-0000-0000-0000-0000000000b1"
    dislike_id = "00000000-0000-0000-0000-0000000000b2"
    await _seed_feedback(
        feedback_id=like_id,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        feedback_value=1,
        message="liked",
    )
    await _seed_feedback(
        feedback_id=dislike_id,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        feedback_value=2,
        message="disliked",
    )

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/feedback",
            params={
                "user_id": "user-1",
                "source_product": "changple5",
                "feedback_value": "2",
            },
        )

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["id"] for record in records] == [dislike_id]
    assert records[0]["comments"] == []


@pytest.mark.anyio
async def test_user_feedback_paginates(configured_database: str) -> None:
    older = "00000000-0000-0000-0000-0000000000c1"
    newer = "00000000-0000-0000-0000-0000000000c2"
    await _seed_feedback(
        feedback_id=older,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="older",
    )
    await _seed_feedback(
        feedback_id=newer,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        message="newer",
    )

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.get(
            "/api/feedback",
            params={"user_id": "user-1", "source_product": "changple5", "limit": "1"},
        )
        first_body = first.json()
        second = await client.get(
            "/api/feedback",
            params={
                "user_id": "user-1",
                "source_product": "changple5",
                "limit": "1",
                "cursor": first_body["next_cursor"],
            },
        )

    assert first.status_code == 200
    assert [record["id"] for record in first_body["records"]] == [newer]
    assert "next_cursor" in first_body

    second_body = second.json()
    assert second.status_code == 200
    assert [record["id"] for record in second_body["records"]] == [older]
    assert "next_cursor" not in second_body


@pytest.mark.anyio
async def test_user_feedback_requires_auth_when_token_configured(
    configured_database: str,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000d1"
    await _seed_feedback(
        feedback_id=feedback_id,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="guarded",
    )

    transport = httpx.ASGITransport(app=make_api_app(token="secret"))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        params = {"user_id": "user-1", "source_product": "changple5"}
        missing = await client.get("/api/feedback", params=params)
        wrong = await client.get(
            "/api/feedback", params=params, headers={"Authorization": "Bearer wrong"}
        )
        allowed = await client.get(
            "/api/feedback", params=params, headers={"Authorization": "Bearer secret"}
        )

    assert missing.status_code == 401
    assert missing.json() == {"detail": "Unauthorized"}
    assert missing.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401
    assert allowed.status_code == 200
    assert [record["id"] for record in allowed.json()["records"]] == [feedback_id]


@pytest.mark.anyio
async def test_user_read_surfaces_only_own_attachments(configured_database: str) -> None:
    mine = "00000000-0000-0000-0000-0000000000b1"
    other_user = "00000000-0000-0000-0000-0000000000b2"
    mine_attachment = "00000000-0000-0000-0000-0000000000b3"

    await _seed_feedback(
        feedback_id=mine,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="mine",
    )
    await _seed_feedback(
        feedback_id=other_user,
        user_id="user-2",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        message="other user",
    )
    await _seed_attachment(
        attachment_id=mine_attachment,
        feedback_id=mine,
        storage_key="mine-key",
        created_at=datetime(2026, 6, 1, 10, 5, tzinfo=UTC),
        filename="mine.png",
    )
    await _seed_attachment(
        attachment_id="00000000-0000-0000-0000-0000000000b4",
        feedback_id=other_user,
        storage_key="other-key",
        created_at=datetime(2026, 6, 1, 11, 5, tzinfo=UTC),
    )

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/feedback",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["id"] for record in records] == [mine]
    attachments = records[0]["attachments"]
    assert [item["id"] for item in attachments] == [mine_attachment]
    assert attachments[0]["filename"] == "mine.png"
    assert (
        attachments[0]["url"]
        == f"/api/feedback/{mine}/attachments/{mine_attachment}"
    )


@pytest.mark.anyio
async def test_user_attachment_download_own_returns_bytes(
    configured_database: str,
    api_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c1"
    attachment_id = "00000000-0000-0000-0000-0000000000c2"
    payload = b"\x89PNG\r\n\x1a\nuser-bytes"
    await _seed_feedback(
        feedback_id=feedback_id,
        user_id="user-1",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="mine",
    )
    await _seed_attachment(
        attachment_id=attachment_id,
        feedback_id=feedback_id,
        storage_key="user-key",
        created_at=datetime(2026, 6, 1, 10, 5, tzinfo=UTC),
        filename="shot.png",
    )
    api_attachment_storage.save("user-key", payload)

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/api/feedback/{feedback_id}/attachments/{attachment_id}",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"].startswith("image/png")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.anyio
async def test_user_attachment_download_other_user_returns_404(
    configured_database: str,
    api_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c3"
    attachment_id = "00000000-0000-0000-0000-0000000000c4"
    await _seed_feedback(
        feedback_id=feedback_id,
        user_id="user-2",
        source_product="changple5",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="other user",
    )
    await _seed_attachment(
        attachment_id=attachment_id,
        feedback_id=feedback_id,
        storage_key="other-user-key",
        created_at=datetime(2026, 6, 1, 10, 5, tzinfo=UTC),
    )
    api_attachment_storage.save("other-user-key", b"secret")

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/api/feedback/{feedback_id}/attachments/{attachment_id}",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_attachment_download_other_product_returns_404(
    configured_database: str,
    api_attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c5"
    attachment_id = "00000000-0000-0000-0000-0000000000c6"
    await _seed_feedback(
        feedback_id=feedback_id,
        user_id="user-1",
        source_product="other-product",
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="other product",
    )
    await _seed_attachment(
        attachment_id=attachment_id,
        feedback_id=feedback_id,
        storage_key="other-product-key",
        created_at=datetime(2026, 6, 1, 10, 5, tzinfo=UTC),
        claimed_source_product="other-product",
    )
    api_attachment_storage.save("other-product-key", b"secret")

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/api/feedback/{feedback_id}/attachments/{attachment_id}",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_attachment_download_missing_scope_returns_400(
    configured_database: str,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c7"
    attachment_id = "00000000-0000-0000-0000-0000000000c8"

    transport = httpx.ASGITransport(app=make_api_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/api/feedback/{feedback_id}/attachments/{attachment_id}",
            params={"user_id": "user-1"},
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_user_attachment_download_requires_bearer_when_configured(
    configured_database: str,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c9"
    attachment_id = "00000000-0000-0000-0000-0000000000ca"

    transport = httpx.ASGITransport(app=make_api_app(token="secret"))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"/api/feedback/{feedback_id}/attachments/{attachment_id}",
            params={"user_id": "user-1", "source_product": "changple5"},
        )

    assert response.status_code == 401
