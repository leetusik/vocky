"""Public REST access routing and bearer-auth tests."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from vocky.app import create_app
from vocky.auth import (
    APIBearerAuthMiddleware,
    AdminBearerAuthMiddleware,
    is_admin_api_path,
    is_api_path,
    is_authorized_bearer,
)
from vocky.config import parse_csv_setting


def test_parse_csv_setting_trims_blanks_and_deduplicates() -> None:
    assert parse_csv_setting(" vocky.example.com, ,vocky.example.com,feedback.example.com ") == (
        "vocky.example.com",
        "feedback.example.com",
    )


def test_path_auth_helpers_match_only_their_path_families_and_bearer_headers() -> None:
    assert is_admin_api_path("/admin/api") is True
    assert is_admin_api_path("/admin/api/feedback") is True
    assert is_admin_api_path("/admin/api/feedback/metrics") is True
    assert is_admin_api_path("/admin") is False
    assert is_admin_api_path("/admin/assets/app.js") is False
    assert is_api_path("/api") is True
    assert is_api_path("/api/feedback") is True
    assert is_api_path("/admin/api/feedback") is False

    assert is_authorized_bearer("Bearer secret", "secret") is True
    assert is_authorized_bearer("bearer secret", "secret") is True
    assert is_authorized_bearer("Bearer wrong", "secret") is False
    assert is_authorized_bearer("Basic secret", "secret") is False
    assert is_authorized_bearer(None, "secret") is False


def test_admin_bearer_auth_middleware_requires_configured_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(
        routes=[
            Route("/healthz", endpoint, methods=["GET"]),
            Route("/admin/api/healthz", endpoint, methods=["GET"]),
            Route("/admin/api/feedback/metrics", endpoint, methods=["GET"]),
        ]
    )
    app.add_middleware(AdminBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    health_response = client.get("/healthz")
    missing_response = client.get("/admin/api/healthz")
    missing_metrics_response = client.get("/admin/api/feedback/metrics")
    wrong_response = client.get(
        "/admin/api/healthz",
        headers={"Authorization": "Bearer wrong"},
    )
    allowed_metrics_response = client.get(
        "/admin/api/feedback/metrics",
        headers={"Authorization": "Bearer secret"},
    )
    allowed_response = client.get(
        "/admin/api/healthz",
        headers={"Authorization": "Bearer secret"},
    )

    assert health_response.status_code == 200
    assert missing_response.status_code == 401
    assert missing_response.headers["www-authenticate"] == "Bearer"
    assert missing_response.json() == {"detail": "Unauthorized"}
    assert missing_metrics_response.status_code == 401
    assert wrong_response.status_code == 401
    assert allowed_metrics_response.status_code == 200
    assert allowed_metrics_response.text == "ok"
    assert allowed_response.status_code == 200
    assert allowed_response.text == "ok"


def test_api_bearer_auth_middleware_allows_disabled_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(routes=[Route("/api/feedback", endpoint, methods=["POST"])])
    app.add_middleware(APIBearerAuthMiddleware, token="")
    client = TestClient(app)

    response = client.post("/api/feedback")

    assert response.status_code == 200
    assert response.text == "ok"


def test_api_bearer_auth_middleware_requires_configured_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(
        routes=[
            Route("/healthz", endpoint, methods=["GET"]),
            Route("/api/feedback", endpoint, methods=["POST"]),
        ]
    )
    app.add_middleware(APIBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    health_response = client.get("/healthz")
    missing_response = client.post("/api/feedback")
    wrong_response = client.post(
        "/api/feedback",
        headers={"Authorization": "Bearer wrong"},
    )
    allowed_response = client.post(
        "/api/feedback",
        headers={"Authorization": "Bearer secret"},
    )

    assert health_response.status_code == 200
    assert missing_response.status_code == 401
    assert missing_response.headers["www-authenticate"] == "Bearer"
    assert missing_response.json() == {"detail": "Unauthorized"}
    assert wrong_response.status_code == 401
    assert allowed_response.status_code == 200
    assert allowed_response.text == "ok"


def test_core_rest_and_admin_routes_are_registered_without_a_catch_all_mount() -> None:
    app = create_app()
    route_paths = [getattr(route, "path", None) for route in app.routes]

    for path in (
        "/healthz",
        "/admin/api/healthz",
        "/admin/api/feedback/metrics",
        "/admin",
        "/admin/assets/app.css",
        "/admin/assets/app.js",
        "/admin/assets/docs.json",
        "/api/feedback",
    ):
        assert path in route_paths

    # The retired MCP server was mounted at "/" (normalized to an empty path);
    # its removal must leave no root catch-all mount behind.
    assert "" not in route_paths
