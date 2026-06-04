"""Attachment storage subsystem exports and dependency wiring."""

from vocky.config import get_settings
from vocky.storage.base import (
    AttachmentStorage,
    StorageError,
    StorageObjectNotFoundError,
)
from vocky.storage.local import LocalFilesystemAttachmentStorage

__all__ = [
    "AttachmentStorage",
    "LocalFilesystemAttachmentStorage",
    "StorageError",
    "StorageObjectNotFoundError",
    "get_attachment_storage",
]


def get_attachment_storage() -> AttachmentStorage:
    """Return the configured attachment storage backend."""

    return LocalFilesystemAttachmentStorage(get_settings().attachments_dir)
