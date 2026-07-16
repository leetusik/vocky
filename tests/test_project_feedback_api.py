"""Project-scoped feedback review + manage REST tests (`/api/project/feedback`)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

from vocky.accounts import (
    CreateProject,
    CreateProjectCredential,
    get_accounts_service,
)
from vocky.accounts.security import generate_opaque_token, sha256_hex
from vocky.auth import ProjectCredentialAuthMiddleware
from vocky.db import get_engine
from vocky.project_feedback_api import routes as project_feedback_routes
from vocky.storage import LocalFilesystemAttachmentStorage


def make_app() -> Starlette:
    """Create a test app with the project routes behind mandatory ingest auth."""

    app = Starlette(routes=project_feedback_routes)
    app.add_middleware(ProjectCredentialAuthMiddleware)
    return app


def _client(key: str) -> httpx.AsyncClient:
    """Return an ASGI client presenting ``key`` as the ingest Bearer token."""

    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=make_app()),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {key}"},
    )


@pytest.fixture
def attachment_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalFilesystemAttachmentStorage:
    """Point the project download route at a temp-dir storage backend."""

    storage = LocalFilesystemAttachmentStorage(tmp_path)
    monkeypatch.setattr(
        "vocky.project_feedback_api.get_attachment_storage", lambda: storage
    )
    return storage


async def _mint_project_credential(tenant_id: UUID) -> tuple[str, UUID]:
    """Create a second project + active credential under ``tenant_id``.

    Returns ``(plaintext_key, project_id)``.
    """

    service = get_accounts_service()
    project = await service.create_project(
        CreateProject(tenant_id=tenant_id, name="second project")
    )
    key = f"vk_{generate_opaque_token()}"
    await service.create_project_credential(
        CreateProjectCredential(
            project_id=project.id,
            token_prefix=key[:12],
            token_hash=sha256_hex(key),
            name="second ingest key",
        )
    )
    return key, project.id


async def _seed_feedback(
    *,
    feedback_id: str,
    project_id: str | None,
    ingested_at: datetime,
    message: str = "feedback row",
    source_product: str = "changple5",
    feedback_value: int | None = None,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events ("
                "id, message, source_product, feedback_value, ingested_at, project_id"
                ") VALUES ("
                ":id, :message, :source_product, :feedback_value, :ingested_at, :project_id"
                ")"
            ),
            {
                "id": feedback_id,
                "message": message,
                "source_product": source_product,
                "feedback_value": feedback_value,
                "ingested_at": ingested_at,
                "project_id": project_id,
            },
        )


async def _seed_attachment(
    *,
    attachment_id: str,
    feedback_id: str,
    storage_key: str,
    created_at: datetime,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_attachments ("
                "id, feedback_id, storage_key, content_type, byte_size, filename, "
                "claimed_user_id, claimed_source_product, created_at"
                ") VALUES ("
                ":id, :feedback_id, :storage_key, 'image/png', 3, NULL, "
                "NULL, 'changple5', :created_at)"
            ),
            {
                "id": attachment_id,
                "feedback_id": feedback_id,
                "storage_key": storage_key,
                "created_at": created_at,
            },
        )


@pytest.mark.anyio
async def test_list_scopes_to_credential_project_and_paginates(
    configured_database: str,
    configured_project_credential,
) -> None:
    _key_b, project_b = await _mint_project_credential(
        configured_project_credential.tenant_id
    )
    older = "00000000-0000-0000-0000-0000000000a1"
    newer = "00000000-0000-0000-0000-0000000000a2"
    other = "00000000-0000-0000-0000-0000000000a3"
    await _seed_feedback(
        feedback_id=older,
        project_id=str(configured_project_credential.project_id),
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="mine older",
    )
    await _seed_feedback(
        feedback_id=newer,
        project_id=str(configured_project_credential.project_id),
        ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        message="mine newer",
    )
    await _seed_feedback(
        feedback_id=other,
        project_id=str(project_b),
        ingested_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        message="project B",
    )

    async with _client(configured_project_credential.key) as client:
        listed = await client.get("/api/project/feedback")
        first = await client.get("/api/project/feedback", params={"limit": "1"})
        first_body = first.json()
        second = await client.get(
            "/api/project/feedback",
            params={"limit": "1", "cursor": first_body["next_cursor"]},
        )

    assert listed.status_code == 200
    # Only project-A rows, newest-first; project-B row excluded.
    assert [r["id"] for r in listed.json()["records"]] == [newer, older]
    assert "project_id" not in listed.json()["records"][0]

    assert first.status_code == 200
    assert [r["id"] for r in first_body["records"]] == [newer]
    assert "next_cursor" in first_body
    second_body = second.json()
    assert [r["id"] for r in second_body["records"]] == [older]
    assert "next_cursor" not in second_body


@pytest.mark.anyio
async def test_cross_project_feedback_returns_404_never_403(
    configured_database: str,
    configured_project_credential,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    _key_b, project_b = await _mint_project_credential(
        configured_project_credential.tenant_id
    )
    other = "00000000-0000-0000-0000-0000000000b1"
    attachment_id = "00000000-0000-0000-0000-0000000000b2"
    await _seed_feedback(
        feedback_id=other,
        project_id=str(project_b),
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        message="project B secret",
    )
    await _seed_attachment(
        attachment_id=attachment_id,
        feedback_id=other,
        storage_key="b-key",
        created_at=datetime(2026, 6, 1, 10, 5, tzinfo=UTC),
    )
    attachment_storage.save("b-key", b"secret")

    async with _client(configured_project_credential.key) as client:
        get_resp = await client.get(f"/api/project/feedback/{other}")
        patch_resp = await client.patch(
            f"/api/project/feedback/{other}", json={"feedback_value": 1}
        )
        delete_resp = await client.delete(f"/api/project/feedback/{other}")
        post_comment = await client.post(
            f"/api/project/feedback/{other}/comments", json={"body": "peek"}
        )
        list_comments = await client.get(f"/api/project/feedback/{other}/comments")
        download = await client.get(
            f"/api/project/feedback/{other}/attachments/{attachment_id}"
        )

    for resp in (
        get_resp,
        patch_resp,
        delete_resp,
        post_comment,
        list_comments,
        download,
    ):
        assert resp.status_code == 404, resp.request.url

    # The project-B row is untouched (delete never happened).
    async with get_engine().begin() as connection:
        remaining = await connection.execute(
            text("SELECT count(*) FROM feedback_events WHERE id = :id"),
            {"id": other},
        )
        assert remaining.scalar_one() == 1


@pytest.mark.anyio
async def test_patch_comment_and_delete_own_feedback(
    configured_database: str,
    configured_project_credential,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000c1"
    await _seed_feedback(
        feedback_id=feedback_id,
        project_id=str(configured_project_credential.project_id),
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        feedback_value=2,
        message="manage me",
    )

    async with _client(configured_project_credential.key) as client:
        patch_resp = await client.patch(
            f"/api/project/feedback/{feedback_id}",
            json={"feedback_value": 1, "comment": " reviewed "},
        )
        post_comment = await client.post(
            f"/api/project/feedback/{feedback_id}/comments",
            json={"author": "  ops  ", "body": "  looked into it  "},
        )
        list_comments = await client.get(
            f"/api/project/feedback/{feedback_id}/comments"
        )
        detail = await client.get(f"/api/project/feedback/{feedback_id}")
        delete_resp = await client.delete(f"/api/project/feedback/{feedback_id}")
        after_delete = await client.get(f"/api/project/feedback/{feedback_id}")

    assert patch_resp.status_code == 200
    record = patch_resp.json()["record"]
    assert record["feedback_value"] == 1
    assert record["comment"] == "reviewed"

    assert post_comment.status_code == 201
    assert post_comment.json()["comment"]["author"] == "ops"
    assert post_comment.json()["comment"]["body"] == "looked into it"

    assert list_comments.status_code == 200
    assert [c["body"] for c in list_comments.json()["comments"]] == ["looked into it"]

    assert detail.status_code == 200
    assert detail.json()["record"]["id"] == feedback_id
    assert len(detail.json()["record"]["comments"]) == 1

    assert delete_resp.status_code == 204
    assert delete_resp.content == b""
    assert after_delete.status_code == 404


@pytest.mark.anyio
async def test_missing_or_invalid_credential_returns_401(
    configured_database: str,
    configured_project_credential,
) -> None:
    feedback_id = "00000000-0000-0000-0000-0000000000d1"
    await _seed_feedback(
        feedback_id=feedback_id,
        project_id=str(configured_project_credential.project_id),
        ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
    )

    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        missing = await client.get("/api/project/feedback")
        wrong = await client.get(
            "/api/project/feedback",
            headers={"Authorization": "Bearer vk_not-a-real-key"},
        )
        allowed = await client.get(
            "/api/project/feedback",
            headers={"Authorization": f"Bearer {configured_project_credential.key}"},
        )

    assert missing.status_code == 401
    assert missing.json() == {"detail": "Unauthorized"}
    assert wrong.status_code == 401
    assert allowed.status_code == 200
    assert [r["id"] for r in allowed.json()["records"]] == [feedback_id]
