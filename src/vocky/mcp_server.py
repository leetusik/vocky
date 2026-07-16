"""FastMCP server bootstrap (transport only; tools land in P7.S2)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

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


settings = get_settings()

# Tool-less transport foundation: a FastMCP server with zero registered tools is
# valid — ``tools/list`` returns empty and ``initialize`` handshakes normally.
# The ``capture_feedback`` tool and its per-project credential auth land in P7.S2.
# ``streamable_http_path="/"`` pairs with a ``Mount("/mcp", ...)`` in ``app.py`` so
# the external endpoint is ``/mcp`` without reintroducing a root catch-all mount.
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
