"""Shared trigger-type validation."""

from __future__ import annotations

ALLOWED_TRIGGER_TYPES = ("like", "dislike", "comment", "rating", "survey", "manual", "other")
TRIGGER_TYPE_VALIDATION_ERROR = f"trigger_type must be one of: {', '.join(ALLOWED_TRIGGER_TYPES)}"


class TriggerTypeValidationError(ValueError):
    """Raised when a trigger type value is not allowed."""


def normalize_trigger_type(value: str | None) -> str | None:
    """Trim trigger type values, collapse blanks to null, and reject unknown categories."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized not in ALLOWED_TRIGGER_TYPES:
        raise TriggerTypeValidationError(TRIGGER_TYPE_VALIDATION_ERROR)
    return normalized
