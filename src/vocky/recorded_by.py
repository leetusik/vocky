"""Shared ``recorded_by`` (who recorded this feedback) validation.

The marker is orthogonal to ``trigger_type`` (*why* capture happened): it answers
*who* recorded the event. ``None`` means **unspecified** — every pre-P14 row and
every caller that stays silent — and is never inferred or backfilled.
"""

from __future__ import annotations

ALLOWED_RECORDED_BY = ("agent", "human")
RECORDED_BY_VALIDATION_ERROR = f"recorded_by must be one of: {', '.join(ALLOWED_RECORDED_BY)}"


class RecordedByValidationError(ValueError):
    """Raised when a recorded_by value is not allowed."""


def normalize_recorded_by(value: str | None) -> str | None:
    """Trim recorded_by values, collapse blanks to null, and reject unknown actors."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized not in ALLOWED_RECORDED_BY:
        raise RecordedByValidationError(RECORDED_BY_VALIDATION_ERROR)
    return normalized
