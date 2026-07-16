"""ASGI application entrypoints."""

from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.admin_api import routes as admin_routes
from vocky.admin_ui import routes as admin_ui_routes
from vocky.api import routes as api_routes
from vocky.app_api import routes as app_api_routes
from vocky.attachments_api import routes as attachment_routes
from vocky.auth import AdminBearerAuthMiddleware, ProjectCredentialAuthMiddleware
from vocky.auth_api import routes as auth_routes
from vocky.config import get_settings
from vocky.db import dispose_engine
from vocky.redis_client import dispose_redis_client


async def healthz(_: Request) -> JSONResponse:
    """Return a simple liveness response."""

    return JSONResponse({"service": "vocky", "status": "ok"})


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    """Dispose shared resources when the host app shuts down."""

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
            *admin_routes,
            *admin_ui_routes,
            *api_routes,
            *attachment_routes,
        ],
        middleware=[
            Middleware(ProjectCredentialAuthMiddleware),
            Middleware(AdminBearerAuthMiddleware, token=settings.admin_auth_token_value),
        ],
        exception_handlers={AuthError: auth_error_handler},
        lifespan=lifespan,
    )


app = create_app()
