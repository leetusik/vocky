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
    assert 'data-refresh-dashboard' in response.text
    assert 'data-dashboard-status' in response.text
    assert 'data-dashboard-window-controls' in response.text
    assert 'data-dashboard-window-days="7"' in response.text
    assert 'data-dashboard-window-days="30"' in response.text
    assert 'data-dashboard-window-days="90"' in response.text
    assert 'data-dashboard-updated' in response.text
    assert 'data-metric-total' in response.text
    assert 'data-metric-liked' in response.text
    assert 'data-metric-disliked' in response.text
    assert 'data-metric-unrated' in response.text
    assert 'data-trend-chart' in response.text
    assert 'data-recent-list' in response.text
    assert 'Recent activity' in response.text
    assert 'data-feedback-filter-form' in response.text
    assert 'data-feedback-filter="start_ingested_at"' in response.text
    assert 'data-feedback-filter="end_ingested_at"' in response.text
    assert 'data-feedback-filter="feedback_value"' in response.text
    assert 'data-feedback-filter="source_product"' in response.text
    assert 'data-feedback-filter="source_integration"' in response.text
    assert 'data-feedback-filter="conversation_id"' in response.text
    assert 'data-feedback-filter="session_id"' in response.text
    assert 'data-feedback-filter="channel"' in response.text
    assert 'data-feedback-filter="tag"' in response.text
    assert 'data-feedback-filter="limit"' in response.text
    assert 'data-feedback-list' in response.text
    assert 'data-feedback-prev' in response.text
    assert 'data-feedback-next' in response.text
    assert 'data-refresh-feedback' in response.text
    assert 'data-feedback-detail' in response.text
    assert 'data-feedback-detail-meta' in response.text
    assert 'Select a record.' in response.text
    assert 'data-docs-root' in response.text
    assert 'data-docs-nav' in response.text
    assert 'data-docs-article' in response.text
    assert 'data-docs-meta' in response.text
    assert 'href="/admin/assets/app.css"' in response.text
    assert 'src="/admin/assets/app.js"' in response.text
    assert slash_response.status_code == 200
    assert slash_response.text == response.text


def test_admin_ui_assets_serve_packaged_resources() -> None:
    client = TestClient(create_app())

    css_response = client.get("/admin/assets/app.css")
    js_response = client.get("/admin/assets/app.js")
    docs_response = client.get("/admin/assets/docs.json")

    assert css_response.status_code == 200
    assert css_response.headers["content-type"].startswith("text/css")
    assert ".admin-app" in css_response.text
    assert ".metric-grid" in css_response.text
    assert ".dashboard-toolbar" in css_response.text
    assert ".window-controls" in css_response.text
    assert ".dashboard-status" in css_response.text
    assert ".dashboard-grid" in css_response.text
    assert ".trend-chart" in css_response.text
    assert ".trend-row" in css_response.text
    assert ".recent-list" in css_response.text
    assert ".feedback-badge" in css_response.text
    assert ".feedback-filter-form" in css_response.text
    assert ".feedback-list" in css_response.text
    assert ".feedback-review-layout" in css_response.text
    assert ".feedback-detail" in css_response.text
    assert ".feedback-json-block" in css_response.text
    assert ".feedback-edit-form" in css_response.text
    assert ".feedback-edit-error" in css_response.text
    assert ".danger-button" in css_response.text
    assert ".feedback-delete-prompt" in css_response.text
    assert ".feedback-pagination" in css_response.text
    assert ".docs-layout" in css_response.text
    assert ".docs-topic-button" in css_response.text
    assert js_response.status_code == 200
    assert js_response.headers["content-type"].startswith("application/javascript")
    assert "[data-admin-shell]" in js_response.text
    assert 'TOKEN_STORAGE_KEY = "vocky.adminToken"' in js_response.text
    assert 'ADMIN_API_PREFIX = "/admin/api/"' in js_response.text
    assert 'DOCS_ASSET_PATH = "/admin/assets/docs.json"' in js_response.text
    assert "DEFAULT_DASHBOARD_WINDOW_DAYS = 30" in js_response.text
    assert "DASHBOARD_WINDOW_PRESETS = [7, 30, 90]" in js_response.text
    assert 'requestAdminJson("/admin/api/healthz"' in js_response.text
    assert "/admin/api/feedback/metrics?" in js_response.text
    assert '"/admin/api/feedback?limit=5"' in js_response.text
    assert "makeFeedbackListPath" in js_response.text
    assert 'start_ingested_at' in js_response.text
    assert 'feedback_value' in js_response.text
    assert 'cursor' in js_response.text
    assert "refreshFeedback" in js_response.text
    assert "selectFeedbackRecord" in js_response.text
    assert "/admin/api/feedback/${encodeURIComponent(selectedId)}" in js_response.text
    assert "renderFeedbackDetailRecord" in js_response.text
    assert "formatTargetSummary" in js_response.text
    assert "Target:" in js_response.text
    assert "target_type" in js_response.text
    assert "target_id" in js_response.text
    assert "target_role" in js_response.text
    assert "target_text" in js_response.text
    assert 'appendDetailSection(container, "Target")' in js_response.text
    assert "dataset.feedbackEditForm" in js_response.text
    assert 'method: "PATCH"' in js_response.text
    assert '"Content-Type": "application/json"' in js_response.text
    assert "feedback_value: feedbackValue ? Number(feedbackValue) : null" in js_response.text
    assert "comment:" in js_response.text
    assert "channel:" in js_response.text
    assert "tags:" in js_response.text
    assert "cancelFeedbackEditMode" in js_response.text
    assert "deleteSelectedFeedbackRecord" in js_response.text
    assert 'method: "DELETE"' in js_response.text
    assert "dataset.feedbackDeleteConfirm" in js_response.text
    assert "Feedback record deleted." in js_response.text
    assert "source_metadata" in js_response.text
    assert "used_context" in js_response.text
    assert "Admin API unauthorized" in js_response.text
    assert "No feedback records match these filters." in js_response.text
    assert "Promise.all" in js_response.text
    assert "error.status === 401" in js_response.text
    assert "No feedback in the last" in js_response.text
    assert "renderTrendChart" in js_response.text
    assert "renderRecentActivity" in js_response.text
    assert "formatFeedbackValue" in js_response.text
    assert "data-metric-total" in js_response.text
    assert 'headers.set("Authorization"' in js_response.text
    assert "fetch(DOCS_ASSET_PATH" in js_response.text
    assert "document.createElement" in js_response.text
    assert docs_response.status_code == 200
    assert docs_response.headers["content-type"].startswith("application/json")

    docs_payload = docs_response.json()
    assert docs_payload["version"] == 1
    topic_ids = [
        topic["id"]
        for section in docs_payload["sections"]
        for topic in section["topics"]
    ]
    assert topic_ids == [
        "operator-overview",
        "mcp-tools",
        "rest-capture",
        "admin-rest",
        "auth-tokens",
        "local-self-hosting",
        "public-custom-domain",
    ]
    for required_text in (
        "/mcp",
        "capture_feedback",
        "list_feedback",
        "summarize_feedback",
        "list_liked_conversations",
        "POST /api/feedback",
        "/admin/api/*",
        "GET /admin/api/feedback/metrics",
        "Browser edit scope",
        "guarded delete",
        "target_type",
        "target_text",
        "target fields",
        "202 Accepted",
        "204 No Content",
        "VOCKY_MCP_AUTH_TOKEN",
        "VOCKY_API_AUTH_TOKEN",
        "VOCKY_ADMIN_AUTH_TOKEN",
        "Authorization: Bearer <token>",
        ".env",
        "make bootstrap",
        "make package-check",
        "/admin",
        "make verify",
        "make external-verify",
        "make external-smoke",
        "make compose-down",
        "uv run vocky",
        "uv run vocky-worker",
        "https://vocky.example.com",
        "VOCKY_EXTERNAL_BASE_URL",
        "VOCKY_MCP_ALLOWED_HOSTS",
        "VOCKY_MCP_ALLOWED_ORIGINS",
    ):
        assert required_text in docs_response.text


def test_admin_ui_routes_are_registered_before_mcp_mount() -> None:
    app = create_app()
    route_paths = [getattr(route, "path", None) for route in app.routes]
    mcp_mount_index = route_paths.index("")

    for path in (
        "/admin/api/healthz",
        "/admin/api/feedback/metrics",
        "/admin",
        "/admin/",
        "/admin/assets/app.css",
        "/admin/assets/app.js",
        "/admin/assets/docs.json",
    ):
        assert route_paths.index(path) < mcp_mount_index

    assert route_paths.index("/admin/api/healthz") < route_paths.index("/admin")
    assert route_paths.index("/admin/api/feedback/metrics") < route_paths.index(
        "/admin/api/feedback/{feedback_id}"
    )


def test_admin_ui_paths_do_not_require_admin_api_bearer_token() -> None:
    app = Starlette(routes=[*admin_api_routes, *admin_ui_routes])
    app.add_middleware(AdminBearerAuthMiddleware, token="secret")
    client = TestClient(app)

    admin_response = client.get("/admin")
    asset_response = client.get("/admin/assets/app.js")
    docs_response = client.get("/admin/assets/docs.json")
    api_response = client.get("/admin/api/healthz")

    assert is_admin_api_path("/admin") is False
    assert is_admin_api_path("/admin/") is False
    assert is_admin_api_path("/admin/assets/app.js") is False
    assert is_admin_api_path("/admin/assets/docs.json") is False
    assert is_admin_api_path("/admin/api/healthz") is True
    assert admin_response.status_code == 200
    assert asset_response.status_code == 200
    assert docs_response.status_code == 200
    assert api_response.status_code == 401
    assert api_response.json() == {"detail": "Unauthorized"}
