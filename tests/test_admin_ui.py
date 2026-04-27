"""Admin Web UI route tests."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

from vocky.admin_api import routes as admin_api_routes
from vocky.admin_ui import routes as admin_ui_routes
from vocky.app import create_app
from vocky.auth import AdminBearerAuthMiddleware, is_admin_api_path


def test_admin_ui_index_routes_serve_packaged_html() -> None:
    client = TestClient(create_app())

    response = client.get("/admin")
    slash_response = client.get("/admin/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<div id="app" class="admin-app"' in response.text
    assert 'data-view-tab="dashboard"' in response.text
    assert 'data-view-tab="feedback"' in response.text
    assert 'data-view-tab="docs"' in response.text
    assert 'data-token-form' in response.text
    assert 'href="/admin/assets/app.css"' in response.text
    assert 'src="/admin/assets/app.js"' in response.text
    assert slash_response.status_code == 200
    assert slash_response.text == response.text


def test_admin_ui_assets_serve_packaged_resources() -> None:
    client = TestClient(create_app())

    css_response = client.get("/admin/assets/app.css")
    js_response = client.get("/admin/assets/app.js")

    assert css_response.status_code == 200
    assert css_response.headers["content-type"].startswith("text/css")
    assert ".admin-app" in css_response.text
    assert ".metric-grid" in css_response.text
    assert js_response.status_code == 200
    assert js_response.headers["content-type"].startswith("application/javascript")
    assert "[data-admin-shell]" in js_response.text
    assert 'TOKEN_STORAGE_KEY = "vocky.adminToken"' in js_response.text
    assert 'ADMIN_API_PREFIX = "/admin/api/"' in js_response.text
    assert 'adminFetch("/admin/api/healthz"' in js_response.text
    assert 'headers.set("Authorization"' in js_response.text


def test_admin_ui_routes_are_registered_before_mcp_mount() -> None:
    app = create_app()
    route_paths = [getattr(route, "path", None) for route in app.routes]
    mcp_mount_index = route_paths.index("")

    for path in (
        "/admin/api/healthz",
        "/admin",
        "/admin/",
        "/admin/assets/app.css",
        "/admin/assets/app.js",
    ):
        assert route_paths.index(path) < mcp_mount_index

    assert route_paths.index("/admin/api/healthz") < route_paths.index("/admin")


def test_admin_ui_paths_do_not_require_admin_api_bearer_token() -> None:
    app = Starlette(routes=[*admin_api_routes, *admin_ui_routes])
    app.add_middleware(AdminBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    admin_response = client.get("/admin")
    asset_response = client.get("/admin/assets/app.js")
    api_response = client.get("/admin/api/healthz")

    assert is_admin_api_path("/admin") is False
    assert is_admin_api_path("/admin/") is False
    assert is_admin_api_path("/admin/assets/app.js") is False
    assert is_admin_api_path("/admin/api/healthz") is True
    assert admin_response.status_code == 200
    assert asset_response.status_code == 200
    assert api_response.status_code == 401
    assert api_response.json() == {"detail": "Unauthorized"}
