"""Simple local smoke checks."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen
from uuid import uuid4

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


DEFAULT_USER_AGENT = "VockySmoke/0.1"


def make_http_user_agent() -> str:
    """Return the user agent used by smoke HTTP clients."""

    return os.getenv("VOCKY_HTTP_USER_AGENT", "").strip() or DEFAULT_USER_AGENT


def parse_timestamp(value: str) -> datetime:
    """Parse a UTC ISO 8601 timestamp from the MCP responses."""

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def serialize_timestamp(value: datetime) -> str:
    """Serialize a UTC ISO 8601 timestamp for MCP requests."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def make_mcp_client_headers(auth_token: str | None = None) -> dict[str, str]:
    """Return optional MCP client headers for smoke checks."""

    headers = {"User-Agent": make_http_user_agent()}
    token = os.getenv("VOCKY_MCP_AUTH_TOKEN", "") if auth_token is None else auth_token
    token = token.strip()
    if not token:
        return headers

    headers["Authorization"] = f"Bearer {token}"
    return headers


def make_smoke_health_request(url: str) -> Request:
    """Build a health-check request with an explicit user agent."""

    return Request(url, headers={"User-Agent": make_http_user_agent()})


async def run_mcp_smoke(base_url: str) -> tuple[str, int, int]:
    """Call the MCP tools through the running app and verify the read/write loop."""

    smoke_session_id = f"smoke-{uuid4()}"
    smoke_message = f"smoke test feedback {smoke_session_id}"
    headers = make_mcp_client_headers()

    async with httpx.AsyncClient(headers=headers, follow_redirects=False) as http_client:
        async with streamable_http_client(f"{base_url}/mcp", http_client=http_client) as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                capture_result = await session.call_tool(
                    "capture_feedback",
                    {
                        "message": smoke_message,
                        "source": {
                            "product": "vocky-smoke",
                            "integration": "make-smoke",
                        },
                        "conversation_id": smoke_session_id,
                        "session_id": smoke_session_id,
                        "tags": ["smoke"],
                        "source_metadata": {"channel": "smoke"},
                    },
                )

                if capture_result.isError:
                    raise SystemExit(
                        f"capture_feedback smoke failed: {capture_result.content[0].text}"
                    )

                capture_payload = capture_result.structuredContent or {}
                request_id = capture_payload.get("request_id")
                accepted_at_raw = capture_payload.get("accepted_at")
                status = capture_payload.get("status")
                if (
                    not isinstance(request_id, str)
                    or not isinstance(accepted_at_raw, str)
                    or status != "accepted"
                ):
                    raise SystemExit(
                        f"capture_feedback smoke returned incomplete data: {capture_result}"
                    )

                accepted_at = parse_timestamp(accepted_at_raw)
                records: list[dict[str, object]] = []
                matched_record: dict[str, object] | None = None

                for _ in range(20):
                    list_result = await session.call_tool(
                        "list_feedback",
                        {
                            "source_product": "vocky-smoke",
                            "session_id": smoke_session_id,
                            "limit": 10,
                        },
                    )
                    if list_result.isError:
                        raise SystemExit(
                            f"list_feedback smoke failed: {list_result.content[0].text}"
                        )

                    list_payload = list_result.structuredContent or {}
                    records = list_payload.get("records")
                    if not isinstance(records, list):
                        raise SystemExit(f"list_feedback smoke returned no records: {list_result}")

                    matching_records = [
                        record
                        for record in records
                        if record.get("message") == smoke_message
                        and record.get("session_id") == smoke_session_id
                    ]
                    if len(matching_records) == 1:
                        matched_record = matching_records[0]
                        break

                    await asyncio.sleep(0.5)

                if matched_record is None:
                    raise SystemExit("list_feedback smoke did not return the worker-persisted record")

                summary_result = await session.call_tool(
                    "summarize_feedback",
                    {
                        "start_ingested_at": serialize_timestamp(accepted_at),
                        "end_ingested_at": serialize_timestamp(accepted_at + timedelta(minutes=5)),
                        "source_product": "vocky-smoke",
                        "session_id": smoke_session_id,
                        "tag": "smoke",
                    },
                )
                if summary_result.isError:
                    raise SystemExit(
                        f"summarize_feedback smoke failed: {summary_result.content[0].text}"
                    )

                summary_payload = summary_result.structuredContent or {}
                total_count = summary_payload.get("total_count")
                daily_counts = summary_payload.get("daily_counts")
                if total_count != 1 or not isinstance(daily_counts, list):
                    raise SystemExit(
                        f"summarize_feedback smoke returned unexpected data: {summary_result}"
                    )

                ingested_at_raw = matched_record.get("ingested_at")
                if not isinstance(ingested_at_raw, str):
                    raise SystemExit(
                        "list_feedback smoke returned a matched record without ingested_at: "
                        f"{list_result}"
                    )

                ingested_day = parse_timestamp(ingested_at_raw).date().isoformat()
                if not any(
                    day_count.get("day") == ingested_day and day_count.get("count") == 1
                    for day_count in daily_counts
                    if isinstance(day_count, dict)
                ):
                    raise SystemExit(
                        "summarize_feedback smoke did not include the captured record day: "
                        f"{summary_result}"
                    )

    return request_id, len(records), total_count


def main() -> None:
    """Verify the local service health endpoint and MCP tools all respond."""

    base_url = os.getenv("VOCKY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    with urlopen(make_smoke_health_request(f"{base_url}/healthz"), timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "ok":
        raise SystemExit(f"unexpected smoke response: {payload}")

    request_id, listed_count, total_count = asyncio.run(run_mcp_smoke(base_url))

    print(f"healthz ok at {base_url}")
    print(f"capture_feedback accepted: {request_id}")
    print(f"list_feedback ok: {listed_count} record(s)")
    print(f"summarize_feedback ok: total_count={total_count}")
