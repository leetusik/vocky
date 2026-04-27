"""Public MCP access routing and transport-security tests."""

from __future__ import annotations

from mcp.server.transport_security import TransportSecurityMiddleware
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from vocky.app import create_app
from vocky.auth import (
    APIBearerAuthMiddleware,
    AdminBearerAuthMiddleware,
    MCPBearerAuthMiddleware,
    is_admin_api_path,
    is_api_path,
    is_authorized_bearer,
    is_mcp_path,
)
from vocky.config import Settings, get_settings, parse_csv_setting
from vocky.mcp_server import make_transport_security_settings
from vocky.smoke import make_mcp_client_headers


def make_settings(
    *,
    allowed_hosts: str = "",
    allowed_origins: str = "",
) -> Settings:
    """Create settings for transport-security tests."""

    return Settings(
        DATABASE_URL="postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky",
        VOCKY_MCP_ALLOWED_HOSTS=allowed_hosts,
        VOCKY_MCP_ALLOWED_ORIGINS=allowed_origins,
    )


def make_configured_mcp_auth_headers() -> dict[str, str]:
    """Return auth headers needed by the app under the current local settings."""

    token = get_settings().mcp_auth_token_value
    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def test_parse_csv_setting_trims_blanks_and_deduplicates() -> None:
    assert parse_csv_setting(" vocky.example.com, ,vocky.example.com,node.example.ts.net ") == (
        "vocky.example.com",
        "node.example.ts.net",
    )


def test_mcp_auth_helpers_match_only_mcp_paths_and_bearer_headers() -> None:
    assert is_mcp_path("/mcp") is True
    assert is_mcp_path("/mcp/") is True
    assert is_mcp_path("/mcp/session") is True
    assert is_mcp_path("/mcp-tools") is False
    assert is_admin_api_path("/admin/api") is True
    assert is_admin_api_path("/admin/api/feedback") is True
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


def test_smoke_mcp_client_headers_use_optional_bearer_token() -> None:
    assert make_mcp_client_headers("") == {"User-Agent": "VockySmoke/0.1"}
    assert make_mcp_client_headers("  ") == {"User-Agent": "VockySmoke/0.1"}
    assert make_mcp_client_headers(" public-secret ") == {
        "User-Agent": "VockySmoke/0.1",
        "Authorization": "Bearer public-secret",
    }


def test_transport_security_allows_configured_public_host_and_origin() -> None:
    security_settings = make_transport_security_settings(
        make_settings(
            allowed_hosts="vocky.example.com,node.example.ts.net",
            allowed_origins="https://vocky.example.com",
        )
    )
    middleware = TransportSecurityMiddleware(security_settings)

    assert middleware._validate_host("vocky.example.com") is True
    assert middleware._validate_host("node.example.ts.net") is True
    assert middleware._validate_host("example.invalid") is False
    assert middleware._validate_origin("https://vocky.example.com") is True
    assert middleware._validate_origin("https://example.invalid") is False


def test_mcp_bearer_auth_middleware_allows_disabled_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(routes=[Route("/mcp", endpoint, methods=["POST"])])
    app.add_middleware(MCPBearerAuthMiddleware, token="")
    client = TestClient(app)

    response = client.post("/mcp")

    assert response.status_code == 200
    assert response.text == "ok"


def test_mcp_bearer_auth_middleware_requires_configured_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(
        routes=[
            Route("/healthz", endpoint, methods=["GET"]),
            Route("/mcp", endpoint, methods=["POST"]),
        ]
    )
    app.add_middleware(MCPBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    health_response = client.get("/healthz")
    missing_response = client.post("/mcp")
    wrong_response = client.post("/mcp", headers={"Authorization": "Bearer wrong"})
    allowed_response = client.post("/mcp", headers={"Authorization": "Bearer secret"})

    assert health_response.status_code == 200
    assert missing_response.status_code == 401
    assert missing_response.headers["www-authenticate"] == "Bearer"
    assert missing_response.json() == {"detail": "Unauthorized"}
    assert wrong_response.status_code == 401
    assert allowed_response.status_code == 200
    assert allowed_response.text == "ok"


def test_admin_bearer_auth_middleware_requires_configured_token() -> None:
    async def endpoint(_) -> Response:
        return Response("ok")

    app = Starlette(
        routes=[
            Route("/healthz", endpoint, methods=["GET"]),
            Route("/admin/api/healthz", endpoint, methods=["GET"]),
        ]
    )
    app.add_middleware(AdminBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    health_response = client.get("/healthz")
    missing_response = client.get("/admin/api/healthz")
    wrong_response = client.get(
        "/admin/api/healthz",
        headers={"Authorization": "Bearer wrong"},
    )
    allowed_response = client.get(
        "/admin/api/healthz",
        headers={"Authorization": "Bearer secret"},
    )

    assert health_response.status_code == 200
    assert missing_response.status_code == 401
    assert missing_response.headers["www-authenticate"] == "Bearer"
    assert missing_response.json() == {"detail": "Unauthorized"}
    assert wrong_response.status_code == 401
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


def test_admin_healthz_route_is_not_handled_by_mcp_mount() -> None:
    app = create_app()
    route_paths = [getattr(route, "path", None) for route in app.routes]

    assert route_paths.index("/admin/api/healthz") < route_paths.index("")
    assert route_paths.index("/admin") < route_paths.index("")
    assert route_paths.index("/admin/assets/app.js") < route_paths.index("")
    assert route_paths.index("/admin/assets/docs.json") < route_paths.index("")
    assert route_paths.index("/api/feedback") < route_paths.index("")


def test_mcp_canonical_path_does_not_redirect_and_rejects_unconfigured_host() -> None:
    auth_headers = make_configured_mcp_auth_headers()

    with TestClient(create_app(), follow_redirects=False) as client:
        response = client.post(
            "/mcp",
            content="{}",
            headers={
                "content-type": "application/json",
                "host": "127.0.0.1:8000",
                **auth_headers,
            },
        )

        rejected_response = client.post(
            "/mcp",
            content="{}",
            headers={
                "content-type": "application/json",
                "host": "example.invalid",
                **auth_headers,
            },
        )

    assert response.status_code != 307
    assert "location" not in response.headers
    assert rejected_response.status_code == 421
    assert rejected_response.text == "Invalid Host header"
