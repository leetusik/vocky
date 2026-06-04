"""Public REST attachment upload route.

Synchronous, scoped image upload. The client uploads each image here to obtain
an ``attachment_id`` before the asynchronous capture path runs; the capture
payload then references the id and the worker links it after persist.
"""

from __future__ import annotations

import contextlib
import logging
from uuid import uuid4

from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vocky.api import require_scope_value
from vocky.config import get_settings
from vocky.feedback import (
    CreateFeedbackAttachment,
    FeedbackPersistenceError,
    get_feedback_service,
)
from vocky.storage import StorageError, get_attachment_storage
from vocky.tools.query_feedback_common import FeedbackQueryValidationError

logger = logging.getLogger(__name__)

_READ_CHUNK = 64 * 1024
# Multipart framing (boundary + part headers) inflates Content-Length beyond the
# raw image, so the cheap pre-check allows some slack; the authoritative cap is
# enforced on the decoded file bytes below.
_MULTIPART_OVERHEAD_SLACK = 8192
_SNIFF_BYTES = 32


def sniff_image_content_type(head: bytes) -> str | None:
    """Return the canonical image MIME type for ``head``, or None if unknown.

    The type is derived from the file's magic bytes, never the client-declared
    part header, so spoofed declarations and text formats such as SVG are
    rejected.
    """

    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _clean_filename(filename: str | None) -> str | None:
    """Strip control characters from a client filename for safe storage."""

    if filename is None:
        return None
    cleaned = "".join(
        ch for ch in filename if ch.isprintable() and ch not in "\r\n"
    ).strip()[:255]
    return cleaned or None


async def upload_attachment(request: Request) -> JSONResponse:
    """Store one uploaded image and return its attachment id (unlinked)."""

    settings = get_settings()
    max_bytes = settings.attachments_max_bytes
    allowed_types = settings.attachments_allowed_mime_type_values

    try:
        user_id = require_scope_value(
            request.query_params.get("user_id"), field_name="user_id"
        )
        source_product = require_scope_value(
            request.query_params.get("source_product"), field_name="source_product"
        )
    except FeedbackQueryValidationError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # Cheap pre-check: reject an obviously-oversized body before reading it.
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            return JSONResponse({"detail": "invalid Content-Length"}, status_code=400)
        if declared > max_bytes + _MULTIPART_OVERHEAD_SLACK:
            return JSONResponse({"detail": "attachment too large"}, status_code=413)

    try:
        form = await request.form(max_files=1, max_fields=1)
    except MultiPartException:
        return JSONResponse({"detail": "invalid multipart upload"}, status_code=400)

    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            return JSONResponse({"detail": "file part is required"}, status_code=400)

        if upload.size is not None and upload.size > max_bytes:
            return JSONResponse({"detail": "attachment too large"}, status_code=413)

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await upload.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                return JSONResponse(
                    {"detail": "attachment too large"}, status_code=413
                )
            chunks.append(chunk)
        data = b"".join(chunks)
        filename = _clean_filename(upload.filename)
    finally:
        await form.close()

    if not data:
        return JSONResponse({"detail": "attachment must not be empty"}, status_code=400)

    content_type = sniff_image_content_type(data[:_SNIFF_BYTES])
    if content_type is None or content_type not in allowed_types:
        return JSONResponse({"detail": "unsupported image type"}, status_code=415)

    storage = get_attachment_storage()
    storage_key = str(uuid4())
    try:
        storage.save(storage_key, data)
    except StorageError:
        logger.exception("attachment storage write failed")
        return JSONResponse(
            {"detail": "attachment storage unavailable"}, status_code=503
        )

    try:
        record = await get_feedback_service().create_unlinked_attachment(
            CreateFeedbackAttachment(
                storage_key=storage_key,
                content_type=content_type,
                byte_size=total,
                filename=filename,
                claimed_user_id=user_id,
                claimed_source_product=source_product,
            )
        )
    except FeedbackPersistenceError:
        with contextlib.suppress(StorageError):
            storage.delete(storage_key)
        logger.exception("attachment row insert failed; deleted orphaned object")
        return JSONResponse(
            {"detail": "attachment storage unavailable"}, status_code=503
        )

    return JSONResponse(
        {
            "attachment_id": str(record.id),
            "content_type": record.content_type,
            "byte_size": record.byte_size,
            "filename": record.filename,
        },
        status_code=201,
    )


routes = [
    Route("/api/feedback/attachments", upload_attachment, methods=["POST"]),
]
