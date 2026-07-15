"""Simple local smoke checks."""

from __future__ import annotations

import json
import os
import time
from urllib.request import Request, urlopen
from uuid import uuid4

import httpx


DEFAULT_USER_AGENT = "VockySmoke/0.1"


def make_http_user_agent() -> str:
    """Return the user agent used by smoke HTTP clients."""

    return os.getenv("VOCKY_HTTP_USER_AGENT", "").strip() or DEFAULT_USER_AGENT


def make_smoke_request_headers(auth_token: str | None = None) -> dict[str, str]:
    """Return REST smoke client headers with an optional bearer token.

    The public REST surface is guarded by ``APIBearerAuthMiddleware``, so the
    Authorization header is included only when ``VOCKY_API_AUTH_TOKEN`` is set.
    """

    headers = {"User-Agent": make_http_user_agent()}
    token = os.getenv("VOCKY_API_AUTH_TOKEN", "") if auth_token is None else auth_token
    token = token.strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def make_smoke_health_request(url: str) -> Request:
    """Build a health-check request with an explicit user agent."""

    return Request(url, headers={"User-Agent": make_http_user_agent()})


def run_rest_smoke(base_url: str) -> tuple[str, int]:
    """Exercise the public REST capture -> persist -> read loop.

    Posts one feedback event to ``POST /api/feedback`` and then polls the scoped
    ``GET /api/feedback`` read until the worker-persisted record appears, asserting
    the captured context round-tripped. Returns the capture request id and the
    number of records returned by the successful read.
    """

    smoke_id = f"smoke-{uuid4()}"
    smoke_message = f"smoke test feedback {smoke_id}"
    smoke_user_id = f"user-{smoke_id}"
    smoke_session_id = f"session-{smoke_id}"
    smoke_target_id = f"{smoke_id}-assistant"
    smoke_target_text = f"smoke target text {smoke_id}"
    headers = make_smoke_request_headers()

    with httpx.Client(headers=headers, follow_redirects=False, timeout=10) as client:
        capture_response = client.post(
            f"{base_url}/api/feedback",
            json={
                "message": smoke_message,
                "source": {"product": "vocky-smoke", "integration": "make-smoke"},
                "session_id": smoke_session_id,
                "user_id": smoke_user_id,
                "target_type": "message",
                "target_id": smoke_target_id,
                "target_role": "assistant",
                "target_text": smoke_target_text,
                "tags": ["smoke"],
            },
        )
        if capture_response.status_code != 202:
            raise SystemExit(
                "capture smoke failed: "
                f"{capture_response.status_code} {capture_response.text}"
            )

        capture_payload = capture_response.json()
        request_id = capture_payload.get("request_id")
        if not isinstance(request_id, str) or capture_payload.get("status") != "accepted":
            raise SystemExit(f"capture smoke returned incomplete data: {capture_payload}")

        matched_record: dict[str, object] | None = None
        records: list[dict[str, object]] = []
        for _ in range(20):
            list_response = client.get(
                f"{base_url}/api/feedback",
                params={
                    "user_id": smoke_user_id,
                    "source_product": "vocky-smoke",
                    "session_id": smoke_session_id,
                    "limit": 10,
                },
            )
            if list_response.status_code != 200:
                raise SystemExit(
                    "list smoke failed: "
                    f"{list_response.status_code} {list_response.text}"
                )

            list_payload = list_response.json()
            records = list_payload.get("records")
            if not isinstance(records, list):
                raise SystemExit(f"list smoke returned no records array: {list_payload}")

            matching = [
                record for record in records if record.get("message") == smoke_message
            ]
            if len(matching) == 1:
                matched_record = matching[0]
                break

            time.sleep(0.5)

        if matched_record is None:
            raise SystemExit("list smoke did not return the worker-persisted record")

        if (
            matched_record.get("user_id") != smoke_user_id
            or matched_record.get("target_type") != "message"
            or matched_record.get("target_id") != smoke_target_id
            or matched_record.get("target_role") != "assistant"
            or matched_record.get("target_text") != smoke_target_text
        ):
            raise SystemExit(
                "list smoke returned a record without round-tripped context: "
                f"{matched_record}"
            )

    return request_id, len(records)


def main() -> None:
    """Verify the local service health endpoint and REST capture/read loop."""

    base_url = os.getenv("VOCKY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    with urlopen(make_smoke_health_request(f"{base_url}/healthz"), timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "ok":
        raise SystemExit(f"unexpected smoke response: {payload}")

    request_id, listed_count = run_rest_smoke(base_url)

    print(f"healthz ok at {base_url}")
    print(f"POST /api/feedback accepted: {request_id}")
    print(f"GET /api/feedback ok: {listed_count} record(s)")
