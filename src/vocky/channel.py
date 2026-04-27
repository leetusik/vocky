"""Shared channel category validation."""

from __future__ import annotations

ALLOWED_CHANNELS = ("web", "mobile", "support")
CHANNEL_VALIDATION_ERROR = f"channel must be one of: {', '.join(ALLOWED_CHANNELS)}"


class ChannelValidationError(ValueError):
    """Raised when a channel write value is not allowed."""


def normalize_channel_write(value: str | None) -> str | None:
    """Trim channel writes, collapse blanks to null, and reject unknown categories."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized not in ALLOWED_CHANNELS:
        raise ChannelValidationError(CHANNEL_VALIDATION_ERROR)
    return normalized
