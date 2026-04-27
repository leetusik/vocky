"""ASGI application entrypoints."""

from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from vocky.admin_api import routes as admin_routes
from vocky.admin_ui import routes as admin_ui_routes
from vocky.api import routes as api_routes
from vocky.auth import APIBearerAuthMiddleware, AdminBearerAuthMiddleware, MCPBearerAuthMiddleware
from vocky.config import get_settings
from vocky.db import dispose_engine
from vocky.mcp_server import mcp
from vocky.redis_client import dispose_redis_client


async def healthz(_: Request) -> JSONResponse:
    """Return a simple liveness response."""

    return JSONResponse({"service": "vocky", "status": "ok"})


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    """Run the FastMCP session manager for the host app lifetime."""

    async with mcp.session_manager.run():
        try:
            yield
        finally:
            await dispose_redis_client()
            await dispose_engine()


def create_app() -> Starlette:
    """Create the Starlette host app."""

    settings = get_settings()

    return Starlette(
        routes=[
            Route("/healthz", healthz),
            *admin_routes,
            *admin_ui_routes,
            *api_routes,
            Mount("/", app=mcp.streamable_http_app()),
        ],
        middleware=[
            Middleware(APIBearerAuthMiddleware, token=settings.api_auth_token_value),
            Middleware(AdminBearerAuthMiddleware, token=settings.admin_auth_token_value),
            Middleware(MCPBearerAuthMiddleware, token=settings.mcp_auth_token_value),
        ],
        lifespan=lifespan,
    )


app = create_app()
