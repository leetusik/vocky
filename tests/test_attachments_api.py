"""Tests for the synchronous attachment upload endpoint."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from starlette.applications import Starlette

from vocky.attachments_api import routes as attachment_routes
from vocky.auth import APIBearerAuthMiddleware
from vocky.config import get_settings
from vocky.db import get_session_maker
from vocky.feedback import FeedbackService
from vocky.storage import LocalFilesystemAttachmentStorage

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SVG_BYTES = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"


def make_attachments_app(*, token: str = "") -> Starlette:
    """Create a test app with the upload route and optional bearer auth."""

    app = Starlette(routes=attachment_routes)
    if token:
        app.add_middleware(APIBearerAuthMiddleware, token=token)
    return app


@pytest.fixture
def attachment_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> LocalFilesystemAttachmentStorage:
    """Point the upload handler at a temp-dir storage backend."""

    storage = LocalFilesystemAttachmentStorage(tmp_path)
    monkeypatch.setattr(
        "vocky.attachments_api.get_attachment_storage", lambda: storage
    )
    return storage


def _client(app: Starlette) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_upload_valid_png_returns_201_and_stores_bytes(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    async with _client(make_attachments_app()) as client:
        response = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "image/png"
    assert body["byte_size"] == len(PNG_BYTES)
    assert body["filename"] == "shot.png"

    service = FeedbackService(get_session_maker())
    record = await service.get_feedback_attachment(UUID(body["attachment_id"]))
    assert record is not None
    assert record.feedback_id is None
    assert record.claimed_user_id == "user-1"
    assert record.claimed_source_product == "changple5"
    assert attachment_storage.load(record.storage_key) == PNG_BYTES


@pytest.mark.asyncio
async def test_upload_spoofed_svg_returns_415(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    async with _client(make_attachments_app()) as client:
        # Declared image/png but the bytes are SVG → sniff rejects it.
        response = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("evil.png", io.BytesIO(SVG_BYTES), "image/png")},
        )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_oversize_returns_413(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOCKY_ATTACHMENTS_MAX_BYTES", "1024")
    get_settings.cache_clear()
    oversize = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096

    async with _client(make_attachments_app()) as client:
        response = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("big.png", io.BytesIO(oversize), "image/png")},
        )

    get_settings.cache_clear()
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_empty_file_returns_400(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    async with _client(make_attachments_app()) as client:
        response = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_missing_file_part_returns_400(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    async with _client(make_attachments_app()) as client:
        response = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"notfile": ("x.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_missing_scope_returns_400(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    async with _client(make_attachments_app()) as client:
        missing_product = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1"},
            files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        missing_user = await client.post(
            "/api/feedback/attachments",
            params={"source_product": "changple5"},
            files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

    assert missing_product.status_code == 400
    assert missing_user.status_code == 400


@pytest.mark.asyncio
async def test_upload_requires_bearer_when_configured(
    configured_database: str,
    attachment_storage: LocalFilesystemAttachmentStorage,
) -> None:
    app = make_attachments_app(token="secret")

    async with _client(app) as client:
        unauthorized = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        authorized = await client.post(
            "/api/feedback/attachments",
            params={"user_id": "user-1", "source_product": "changple5"},
            files={"file": ("shot.png", io.BytesIO(PNG_BYTES), "image/png")},
            headers={"Authorization": "Bearer secret"},
        )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 201
