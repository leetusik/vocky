#!/usr/bin/env python3
"""Wait for the local Vocky health endpoint to report ready."""

from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = "VockySmoke/0.1"


def make_health_request(url: str) -> Request:
    """Build a health-check request with an explicit user agent."""

    return Request(
        url,
        headers={
            "User-Agent": os.getenv("VOCKY_HTTP_USER_AGENT", "").strip()
            or DEFAULT_USER_AGENT
        },
    )


def main() -> None:
    """Poll the configured health endpoint until it reports ready or times out."""

    base_url = os.getenv("VOCKY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    try:
        timeout_seconds = int(os.getenv("WAIT_READY_TIMEOUT", "60"))
    except ValueError as exc:
        raise SystemExit("WAIT_READY_TIMEOUT must be an integer number of seconds.") from exc

    deadline = time.monotonic() + timeout_seconds
    last_error = "service not ready"

    while time.monotonic() < deadline:
        try:
            with urlopen(make_health_request(f"{base_url}/healthz"), timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

            if payload.get("status") == "ok":
                print(f"healthz ok at {base_url}")
                return

            last_error = f"unexpected health payload: {payload}"
        except (HTTPError, URLError, OSError, ValueError) as exc:
            last_error = str(exc)

        time.sleep(1)

    raise SystemExit(f"service did not become ready at {base_url}: {last_error}")


if __name__ == "__main__":
    main()
