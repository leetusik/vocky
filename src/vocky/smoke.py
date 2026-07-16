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


def make_smoke_health_request(url: str) -> Request:
    """Build a health-check request with an explicit user agent."""

    return Request(url, headers={"User-Agent": make_http_user_agent()})


def _provision_ingest_key(client: httpx.Client, base_url: str, smoke_id: str) -> str:
    """Sign up, create a project, and mint a per-project ingest key.

    Public ``/api/*`` capture requires a per-project credential (there is no
    global capture token), so the smoke first walks the account control-plane to
    obtain a real ``vk_`` key. Returns the plaintext key.
    """

    signup_response = client.post(
        f"{base_url}/auth/signup",
        json={
            "email": f"smoke-{smoke_id}@example.com",
            "password": f"smoke-password-{smoke_id}",
        },
    )
    if signup_response.status_code != 201:
        raise SystemExit(
            f"signup smoke failed: {signup_response.status_code} {signup_response.text}"
        )
    token = signup_response.json().get("token")
    if not isinstance(token, str) or not token:
        raise SystemExit(f"signup smoke returned no token: {signup_response.text}")
    user_auth = {"Authorization": f"Bearer {token}"}

    project_response = client.post(
        f"{base_url}/app/projects",
        headers=user_auth,
        json={"name": f"smoke project {smoke_id}"},
    )
    if project_response.status_code != 201:
        raise SystemExit(
            f"project smoke failed: {project_response.status_code} {project_response.text}"
        )
    project_id = project_response.json().get("project", {}).get("id")
    if not isinstance(project_id, str) or not project_id:
        raise SystemExit(f"project smoke returned no id: {project_response.text}")

    credential_response = client.post(
        f"{base_url}/app/projects/{project_id}/credentials",
        headers=user_auth,
        json={"name": "smoke key"},
    )
    if credential_response.status_code != 201:
        raise SystemExit(
            "credential smoke failed: "
            f"{credential_response.status_code} {credential_response.text}"
        )
    api_key = credential_response.json().get("key")
    if not isinstance(api_key, str) or not api_key.startswith("vk_"):
        raise SystemExit(f"credential smoke returned no key: {credential_response.text}")
    return api_key


def run_rest_smoke(base_url: str) -> tuple[str, int]:
    """Exercise the account + public REST capture -> persist -> read loop.

    Provisions a user, project, and per-project ingest key via ``/auth`` and
    ``/app``, then posts one feedback event to ``POST /api/feedback`` with that
    key and polls the scoped ``GET /api/feedback`` read until the worker-persisted
    record appears, asserting the captured context round-tripped. Returns the
    capture request id and the number of records returned by the successful read.
    """

    smoke_id = f"smoke-{uuid4()}"
    smoke_message = f"smoke test feedback {smoke_id}"
    smoke_user_id = f"user-{smoke_id}"
    smoke_session_id = f"session-{smoke_id}"
    smoke_target_id = f"{smoke_id}-assistant"
    smoke_target_text = f"smoke target text {smoke_id}"

    with httpx.Client(
        headers={"User-Agent": make_http_user_agent()},
        follow_redirects=False,
        timeout=10,
    ) as client:
        api_key = _provision_ingest_key(client, base_url, smoke_id)
        api_auth = {"Authorization": f"Bearer {api_key}"}

        capture_response = client.post(
            f"{base_url}/api/feedback",
            headers=api_auth,
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
                headers=api_auth,
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
