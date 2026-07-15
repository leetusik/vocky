"""Password hashing and opaque-token primitives for account auth.

Pure functions with no HTTP or persistence surface. ``hash_password`` /
``verify_password`` wrap argon2id (``argon2-cffi``); ``generate_opaque_token``
mints a high-entropy bearer token and ``sha256_hex`` derives the at-rest hash
that persistence stores (raw tokens are never persisted). S4 reuses
``sha256_hex`` and ``generate_opaque_token`` for project credentials.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2id hash of ``password`` for at-rest storage."""

    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return whether ``password`` matches the stored ``password_hash``.

    Returns ``False`` (never raises) on a mismatch or a malformed stored hash,
    so login can answer an identical generic 401 without leaking which failed.
    """

    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_opaque_token() -> str:
    """Return a new high-entropy, URL-safe opaque bearer token."""

    return secrets.token_urlsafe(32)


def sha256_hex(raw: str) -> str:
    """Return the hex-encoded sha256 digest of ``raw`` (the at-rest token hash)."""

    return hashlib.sha256(raw.encode()).hexdigest()
