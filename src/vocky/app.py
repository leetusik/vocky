"""ASGI application entrypoints."""

from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

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

    return Starlette(
        routes=[
            Route("/healthz", healthz),
            Mount("/mcp", app=mcp.streamable_http_app()),
        ],
        lifespan=lifespan,
    )


app = create_app()
