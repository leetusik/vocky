"""FastMCP server bootstrap."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from mcp import types as mcp_types
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError, UrlElicitationRequiredError

from vocky.config import get_settings


def make_error_result(message: str) -> mcp_types.ServerResult:
    """Return an MCP tool execution error result."""

    return mcp_types.ServerResult(
        mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=message)],
            isError=True,
        )
    )


def install_protocol_aware_call_handler(server: FastMCP) -> None:
    """Install a tools/call handler that keeps unknown-tool failures as protocol errors."""

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

mcp = FastMCP(
    settings.app_name,
    instructions=(
        "Capture user feedback from agent interactions and store it for later review."
    ),
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
)

from vocky.tools import capture_feedback as _capture_feedback  # noqa: E402,F401

install_protocol_aware_call_handler(mcp)
