"""ASGI application entrypoints."""

from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.admin_api import routes as admin_routes
from vocky.api import routes as api_routes
from vocky.app_api import routes as app_api_routes
from vocky.app_feedback_api import routes as app_feedback_routes
from vocky.attachments_api import routes as attachment_routes
from vocky.auth import AdminBearerAuthMiddleware, ProjectCredentialAuthMiddleware
from vocky.auth_api import routes as auth_routes
from vocky.config import get_settings
from vocky.db import dispose_engine
from vocky.mcp_server import mcp
from vocky.project_feedback_api import routes as project_feedback_routes
from vocky.redis_client import dispose_redis_client
from vocky.usage_api import routes as usage_routes


async def healthz(_: Request) -> JSONResponse:
    """Return a simple liveness response."""

    return JSONResponse({"service": "vocky", "status": "ok"})


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    """Run the FastMCP session manager for the host app lifetime, then dispose resources.

    ``session_manager.run()`` MUST wrap the whole app lifetime or the mounted
    Streamable-HTTP app 500s at request time; a mounted sub-app's own lifespan is
    not triggered by the host, so the host nests it here.
    """

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
            *auth_routes,
            *app_api_routes,
            *app_feedback_routes,
            *usage_routes,
            *admin_routes,
            *api_routes,
            *project_feedback_routes,
            *attachment_routes,
            # Mount the FastMCP Streamable-HTTP sub-app at ``/mcp`` (last route so it
            # cannot shadow the core routes). The sub-app serves at its inner
            # ``streamable_http_path="/"``, so the external endpoint is ``/mcp``.
            Mount("/mcp", app=mcp.streamable_http_app()),
        ],
        middleware=[
            Middleware(ProjectCredentialAuthMiddleware),
            Middleware(AdminBearerAuthMiddleware, token=settings.admin_auth_token_value),
        ],
        exception_handlers={AuthError: auth_error_handler},
        lifespan=lifespan,
    )


app = create_app()
