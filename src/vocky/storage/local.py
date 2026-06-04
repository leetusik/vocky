"""Local-filesystem attachment storage backend."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from vocky.storage.base import (
    AttachmentStorage,
    StorageError,
    StorageObjectNotFoundError,
)


class LocalFilesystemAttachmentStorage(AttachmentStorage):
    """Store attachment bytes as files under a single root directory."""

    def __init__(self, root_dir: str | os.PathLike[str]) -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        """Resolve ``key`` to a path inside the root, rejecting traversal."""

        if not key or os.path.isabs(key):
            raise StorageError(f"invalid storage key: {key!r}")

        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise StorageError(f"storage key escapes root: {key!r}")

        return candidate

    def save(self, key: str, data: bytes) -> None:
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write to a sibling temp file then atomically replace, so a reader
        # never observes a partially written object.
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, target)
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise StorageError(f"failed to write storage object: {key!r}") from exc

    def load(self, key: str) -> bytes:
        target = self._resolve_key(key)
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise StorageObjectNotFoundError(
                f"storage object not found: {key!r}"
            ) from exc
        except OSError as exc:
            raise StorageError(f"failed to read storage object: {key!r}") from exc

    def delete(self, key: str) -> None:
        target = self._resolve_key(key)
        try:
            target.unlink()
        except FileNotFoundError as exc:
            raise StorageObjectNotFoundError(
                f"storage object not found: {key!r}"
            ) from exc
        except OSError as exc:
            raise StorageError(f"failed to delete storage object: {key!r}") from exc
