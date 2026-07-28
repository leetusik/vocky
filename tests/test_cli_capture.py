"""`vocky capture` command tests.

Terse, high-value cases only — no live server. Drives the Typer app through
``CliRunner`` with `/api/feedback` stubbed by ``httpx.MockTransport`` (injected
by patching the client factory, same shape as ``tests/test_cli_projects.py``).
"""

from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from vocky.cli import config_store
from vocky.cli.app import app
from vocky.cli.client import ApiClient
from vocky.cli.context import CliContext

runner = CliRunner()


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """Point the config store at a throwaway dir; keep VOCKY_API_TOKEN unset by default."""

    monkeypatch.setenv("VOCKY_CONFIG_DIR", str(tmp_path / "vocky"))
    monkeypatch.delenv("VOCKY_BASE_URL", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("VOCKY_API_TOKEN", raising=False)
    config_store.set_token("sess-live")


def _stub_api(monkeypatch, handler):
    """Route every CLI HTTP call through a MockTransport running ``handler``."""

    def fake_make_client(self, *, token=None, use_stored_token=True):
        effective = token
        if effective is None and use_stored_token:
            effective = config_store.get_token()
        return ApiClient(
            self.base_url, token=effective, transport=httpx.MockTransport(handler)
        )

    monkeypatch.setattr(CliContext, "make_client", fake_make_client)


def test_capture_happy_path_posts_and_prints_request_id(config_env, monkeypatch):
    monkeypatch.setenv("VOCKY_API_TOKEN", "vk_test1234567890")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/feedback"
        body = json.loads(request.content)
        assert body["source"] == {"product": "checkout-web"}
        assert body["message"] == "hi"
        assert request.headers["Authorization"] == "Bearer vk_test1234567890"
        return httpx.Response(
            202,
            json={
                "request_id": "req-1",
                "accepted_at": "2026-07-29T00:00:00+00:00",
                "status": "accepted",
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["capture", "hi", "--product", "checkout-web"])

    assert result.exit_code == 0, result.output
    assert "req-1" in result.stdout


def test_capture_missing_token_fails_without_http_call(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("must not hit the API without a VOCKY_API_TOKEN")

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["capture", "hi", "--product", "checkout-web"])

    assert result.exit_code != 0
    assert "VOCKY_API_TOKEN" in result.stderr


def test_capture_401_names_env_var_not_login(config_env, monkeypatch):
    monkeypatch.setenv("VOCKY_API_TOKEN", "vk_bad")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid credential"})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["capture", "hi", "--product", "checkout-web"])

    assert result.exit_code != 0
    assert "VOCKY_API_TOKEN" in result.stderr
    assert "vocky login" not in result.stderr
