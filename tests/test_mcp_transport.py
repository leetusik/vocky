"""Functional check that the mounted FastMCP transport serves ``/mcp``.

Tool-less foundation (P7.S1): the endpoint handshakes and lists zero tools; the
``capture_feedback`` tool and its per-project credential auth land in P7.S2.
"""

from __future__ import annotations

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from vocky.app import create_app
from vocky.mcp_server import mcp


@pytest.mark.anyio
async def test_mcp_mount_serves_initialize_handshake_with_zero_tools() -> None:
    app = create_app()

    # In-process ASGI transport; the ``:8000`` Host satisfies the DNS-rebinding
    # allowlist (``127.0.0.1:*``) and follow_redirects handles ``/mcp`` -> ``/mcp/``.
    http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        follow_redirects=True,
    )

    # The host app nests ``session_manager.run()`` in its lifespan; ASGITransport
    # does not drive the lifespan, so run it explicitly around the handshake.
    async with http_client, mcp.session_manager.run():
        async with streamable_http_client(
            "http://127.0.0.1:8000/mcp", http_client=http_client
        ) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = await session.list_tools()

    assert init.serverInfo.name == "Vocky"
    assert tools.tools == []
