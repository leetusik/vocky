"""Attachment storage seam.

Defines the storage-backend interface used by the attachment subsystem. The
local-filesystem backend is the only implementation today; an S3-compatible
backend can be added later behind this same interface without touching callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageError(RuntimeError):
    """Raised when an attachment object cannot be written, read, or deleted."""


class StorageObjectNotFoundError(StorageError):
    """Raised when a requested attachment object does not exist."""


class AttachmentStorage(ABC):
    """Backend-neutral interface for storing attachment bytes."""

    @abstractmethod
    def save(self, key: str, data: bytes) -> None:
        """Persist ``data`` under ``key``, overwriting any existing object."""

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Return the bytes stored under ``key``.

        Raises ``StorageObjectNotFoundError`` when no object exists for ``key``.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object stored under ``key``.

        Raises ``StorageObjectNotFoundError`` when no object exists for ``key``.
        """
