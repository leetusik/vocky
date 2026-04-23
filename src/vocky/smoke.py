"""Simple local smoke checks."""

from __future__ import annotations

import asyncio
import json
import os
from urllib.request import urlopen

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run_mcp_smoke(base_url: str) -> str:
    """Call the capture tool through MCP and return the stored feedback id."""

    async with streamable_http_client(f"{base_url}/mcp") as streams:
        read_stream, write_stream, _ = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "capture_feedback",
                {
                    "message": "smoke test feedback",
                    "source": {
                        "product": "vocky-smoke",
                        "integration": "make-smoke",
                    },
                    "tags": ["smoke"],
                    "source_metadata": {"channel": "smoke"},
                },
            )

    if result.isError:
        raise SystemExit(f"mcp smoke failed: {result.content[0].text}")

    structured = result.structuredContent or {}
    feedback_id = structured.get("feedback_id")
    if not isinstance(feedback_id, str):
        raise SystemExit(f"mcp smoke returned no feedback_id: {result}")

    return feedback_id


def main() -> None:
    """Verify the local service health endpoint and MCP tool both respond."""

    base_url = os.getenv("VOCKY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    with urlopen(f"{base_url}/healthz", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "ok":
        raise SystemExit(f"unexpected smoke response: {payload}")

    feedback_id = asyncio.run(run_mcp_smoke(base_url))

    print(f"healthz ok at {base_url}")
    print(f"capture_feedback ok: {feedback_id}")
