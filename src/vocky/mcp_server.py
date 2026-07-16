"""FastMCP server bootstrap for the write-only ``/mcp`` capture surface."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from mcp import types as mcp_types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import McpError, UrlElicitationRequiredError

from vocky.config import Settings, get_settings


DEFAULT_MCP_ALLOWED_HOSTS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
DEFAULT_MCP_ALLOWED_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)


def append_unique(values: tuple[str, ...], additions: tuple[str, ...]) -> list[str]:
    """Return values plus additions while preserving order and removing duplicates."""

    merged = list(values)
    for addition in additions:
        if addition not in merged:
            merged.append(addition)

    return merged


def make_transport_security_settings(settings: Settings) -> TransportSecuritySettings:
    """Build explicit MCP transport security settings for local and public hosts."""

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=append_unique(
            DEFAULT_MCP_ALLOWED_HOSTS,
            settings.mcp_allowed_host_values,
        ),
        allowed_origins=append_unique(
            DEFAULT_MCP_ALLOWED_ORIGINS,
            settings.mcp_allowed_origin_values,
        ),
    )


def make_error_result(message: str) -> mcp_types.ServerResult:
    """Return an MCP tool execution error result."""

    return mcp_types.ServerResult(
        mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=message)],
            isError=True,
        )
    )


def install_protocol_aware_call_handler(server: FastMCP) -> None:
    """Install a tools/call handler that keeps unknown-tool failures as protocol errors.

    It is also what lets a tool return a raw ``CallToolResult`` (used by
    ``capture_feedback`` for structured receipts and validation errors): the
    handler passes such a result straight through as the ``ServerResult``.
    """

    async def handler(req: mcp_types.CallToolRequest) -> mcp_types.ServerResult:
        tool_name = req.params.name
        arguments = req.params.arguments or {}
        tool = server._tool_manager.get_tool(tool_name)

        if tool is None:
            raise McpError(
                mcp_types.ErrorData(
                    code=mcp_types.INVALID_PARAMS,
                    message=f"Unknown tool: {tool_name}",
                    data=None,
                )
            )

        try:
            results = await server.call_tool(tool_name, arguments)
        except UrlElicitationRequiredError:
            raise
        except Exception as exc:
            return make_error_result(str(exc))

        unstructured_content: Sequence[mcp_types.ContentBlock]
        structured_content: dict[str, Any] | None

        if isinstance(results, mcp_types.CallToolResult):
            return mcp_types.ServerResult(results)
        if isinstance(results, tuple) and len(results) == 2:
            unstructured_content, structured_content = results
        elif isinstance(results, dict):
            structured_content = results
            unstructured_content = [
                mcp_types.TextContent(type="text", text=json.dumps(results, indent=2))
            ]
        else:
            unstructured_content = results
            structured_content = None

        if tool.output_schema is not None and structured_content is None:
            return make_error_result(
                "Output validation error: outputSchema defined but no structured output returned"
            )

        return mcp_types.ServerResult(
            mcp_types.CallToolResult(
                content=list(unstructured_content),
                structuredContent=structured_content,
                isError=False,
            )
        )

    server._mcp_server.request_handlers[mcp_types.CallToolRequest] = handler


settings = get_settings()

# Write-only MCP surface: a single ``capture_feedback`` tool feeds the shared
# capture queue, scoped to the per-project ``vk_`` credential the transport
# authenticates. ``streamable_http_path="/"`` pairs with a ``Mount("/mcp", ...)``
# in ``app.py`` so the external endpoint is ``/mcp`` without reintroducing a root
# catch-all mount. The three retired read tools stay retired (reads are REST-only).
mcp = FastMCP(
    settings.app_name,
    instructions=(
        "Capture user feedback from agent interactions through the MCP capture tool."
    ),
    host=settings.host,
    port=settings.port,
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=make_transport_security_settings(settings),
)

# Side-effect registration of the ``capture_feedback`` tool onto ``mcp``.
from vocky.tools import capture_feedback as _capture_feedback  # noqa: E402,F401

install_protocol_aware_call_handler(mcp)
