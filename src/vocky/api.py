"""Public REST API routes."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vocky.capture import (
    CaptureFeedbackInput,
    CaptureFeedbackValidationError,
    normalize_payload,
    serialize_capture_receipt,
)
from vocky.capture_queue import CaptureQueueError, get_capture_queue

logger = logging.getLogger(__name__)


class CaptureAPIValidationError(ValueError):
    """Raised when a REST capture request body is invalid."""


def format_pydantic_error(exc: ValidationError) -> str:
    """Format the first Pydantic validation error for REST clients."""

    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    message = str(first_error.get("msg", "invalid value"))
    if location:
        return f"{location}: {message}"
    return message


async def parse_capture_request(request: Request) -> CaptureFeedbackInput:
    """Parse and validate the JSON request body shape."""

    try:
        raw_body = await request.json()
    except json.JSONDecodeError as exc:
        raise CaptureAPIValidationError("request body must be valid JSON") from exc

    if not isinstance(raw_body, dict):
        raise CaptureAPIValidationError("request body must be a JSON object")

    try:
        return CaptureFeedbackInput.model_validate(raw_body)
    except ValidationError as exc:
        raise CaptureAPIValidationError(format_pydantic_error(exc)) from exc


async def capture_feedback(request: Request) -> JSONResponse:
    """Capture a single feedback event through REST."""

    try:
        raw_payload = await parse_capture_request(request)
        normalized = normalize_payload(raw_payload)
    except (CaptureAPIValidationError, CaptureFeedbackValidationError) as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    try:
        receipt = await get_capture_queue().enqueue_feedback(normalized.payload)
    except CaptureQueueError:
        logger.exception("Failed to enqueue captured feedback event")
        return JSONResponse({"detail": "capture queue unavailable"}, status_code=503)

    response = serialize_capture_receipt(
        request_id=receipt.request_id,
        accepted_at=receipt.accepted_at,
    )
    return JSONResponse(response.model_dump(mode="json"), status_code=202)


routes = [
    Route("/api/feedback", capture_feedback, methods=["POST"]),
]
