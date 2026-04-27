"""Admin Web UI routes."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route

RESOURCE_PACKAGE = "vocky.admin_assets"


@lru_cache(maxsize=None)
def read_resource_text(name: str) -> str:
    """Read a packaged Admin Web UI resource."""

    return files(RESOURCE_PACKAGE).joinpath(name).read_text(encoding="utf-8")


async def admin_index(_: Request) -> HTMLResponse:
    """Serve the Admin Web UI shell."""

    return HTMLResponse(read_resource_text("index.html"))


async def admin_styles(_: Request) -> Response:
    """Serve the Admin Web UI stylesheet."""

    return Response(read_resource_text("app.css"), media_type="text/css")


async def admin_script(_: Request) -> Response:
    """Serve the Admin Web UI script."""

    return Response(read_resource_text("app.js"), media_type="application/javascript")


routes = [
    Route("/admin", admin_index, methods=["GET"]),
    Route("/admin/", admin_index, methods=["GET"]),
    Route("/admin/assets/app.css", admin_styles, methods=["GET"]),
    Route("/admin/assets/app.js", admin_script, methods=["GET"]),
]
