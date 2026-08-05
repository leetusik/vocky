"""End-to-end proof of the authed, write-only ``/mcp`` capture path.

This is the phase crux: an agent presenting a project's ``vk_`` credential at
``/mcp`` calls ``capture_feedback`` and the event lands on the shared capture
queue stamped with the authenticating credential's ``project_id``. It is also
the sole caller of ``mcp.session_manager.run()`` in the suite (once per process
on the shared module-level ``mcp`` singleton).
"""

from __future__ import annotations

import fakeredis.aioredis
import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

import vocky.tools.capture_feedback as capture_tool
from vocky.app import create_app
from vocky.capture_queue import CaptureQueue
from vocky.mcp_server import mcp


@pytest.mark.anyio
async def test_mcp_capture_feedback_enqueues_with_authenticating_project_id(
    monkeypatch: pytest.MonkeyPatch,
    configured_project_credential,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(capture_tool, "get_capture_queue", lambda: queue)

    app = create_app()

    # In-process ASGI transport; the ``:8000`` Host satisfies the DNS-rebinding
    # allowlist (``127.0.0.1:*``) and follow_redirects handles ``/mcp`` -> ``/mcp/``.
    # The ``vk_`` bearer authenticates the whole MCP transport (initialize included).
    http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        follow_redirects=True,
        headers={"Authorization": f"Bearer {configured_project_credential.key}"},
    )

    async with http_client, mcp.session_manager.run():
        async with streamable_http_client(
            "http://127.0.0.1:8000/mcp", http_client=http_client
        ) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "capture_feedback",
                    {
                        "message": "The export flow is broken",
                        "source": {"product": "vocky-agent", "integration": "pytest"},
                        "feedback_value": 2,
                        "user_id": "user_123",
                    },
                )

    assert init.serverInfo.name == "Vocky"
    # Write-only surface: exactly the one capture tool, no revived read tools.
    assert [tool.name for tool in tools.tools] == ["capture_feedback"]
    # The agent marker is advertised in the tool schema (the flat tool signature is
    # what MCP publishes — adding the field to the input model alone would not).
    assert "recorded_by" in tools.tools[0].inputSchema["properties"]

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "accepted"

    # The empirical proof the credential reaches the tool: the enqueued job carries
    # the authenticating credential's project_id (survives serialize -> deserialize).
    queued_job = await queue.pop_job(timeout_seconds=1)
    assert queued_job is not None
    assert queued_job.payload.project_id == configured_project_credential.project_id
    assert queued_job.payload.message == "The export flow is broken"
    assert queued_job.payload.source_product == "vocky-agent"
    assert queued_job.payload.feedback_value == 2
    # The call above omits recorded_by: /mcp is the agent-runtime surface, so the
    # normalizer stamps "agent" rather than leaving the row unspecified.
    assert queued_job.payload.recorded_by == "agent"

    await redis_client.aclose()
