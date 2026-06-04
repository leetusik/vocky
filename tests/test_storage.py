"""Tests for the local-filesystem attachment storage backend."""

from __future__ import annotations

from pathlib import Path

import pytest

from vocky.storage import (
    LocalFilesystemAttachmentStorage,
    StorageError,
    StorageObjectNotFoundError,
)


def test_save_and_load_round_trip_with_binary(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)
    payload = b"\xff\xd8\xff\x00\x01\x02\x03\xfe"

    storage.save("object-1", payload)

    assert storage.load("object-1") == payload


def test_load_unknown_key_raises_not_found(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)

    with pytest.raises(StorageObjectNotFoundError):
        storage.load("missing")


def test_relative_traversal_key_rejected(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save("../escape", b"data")


def test_absolute_key_rejected(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save("/etc/passwd", b"data")


def test_save_creates_intermediate_directories(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)

    storage.save("nested/dir/object.bin", b"payload")

    assert storage.load("nested/dir/object.bin") == b"payload"
    assert (tmp_path / "nested" / "dir" / "object.bin").is_file()


def test_save_overwrites_atomically(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)
    storage.save("object", b"first")

    storage.save("object", b"second")

    assert storage.load("object") == b"second"
    # No partial temp files leak alongside the object.
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".tmp-")]
    assert leftovers == []


def test_delete_removes_object(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)
    storage.save("object", b"payload")

    storage.delete("object")

    with pytest.raises(StorageObjectNotFoundError):
        storage.load("object")


def test_delete_unknown_key_raises_not_found(tmp_path: Path) -> None:
    storage = LocalFilesystemAttachmentStorage(tmp_path)

    with pytest.raises(StorageObjectNotFoundError):
        storage.delete("missing")


def test_root_directory_created_on_init(tmp_path: Path) -> None:
    root = tmp_path / "does" / "not" / "exist" / "yet"

    LocalFilesystemAttachmentStorage(root)

    assert root.is_dir()
