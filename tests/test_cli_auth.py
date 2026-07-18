"""Auth-command tests for the ``vocky`` CLI: signup / login / logout / whoami.

Terse, high-value cases only — no live server. Drives the Typer app through
``CliRunner`` with the API stubbed by ``httpx.MockTransport`` (injected by
patching the client factory) and the config store pointed at a throwaway
``VOCKY_CONFIG_DIR`` so the real ``~`` is never touched.
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
    """Point the config store at a throwaway dir; never touch the real ~."""

    monkeypatch.setenv("VOCKY_CONFIG_DIR", str(tmp_path / "vocky"))
    monkeypatch.delenv("VOCKY_BASE_URL", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


def _stub_api(monkeypatch, handler):
    """Route every CLI HTTP call through a MockTransport running ``handler``.

    Mirrors the real factory's token resolution, only swapping in the transport.
    """

    def fake_make_client(self, *, token=None, use_stored_token=True):
        effective = token
        if effective is None and use_stored_token:
            effective = config_store.get_token()
        return ApiClient(
            self.base_url, token=effective, transport=httpx.MockTransport(handler)
        )

    monkeypatch.setattr(CliContext, "make_client", fake_make_client)


def test_signup_stores_token_and_reports_workspace(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/signup"
        assert json.loads(request.content) == {
            "email": "cli@example.com",
            "password": "pw-at-least-8",
        }
        assert "Authorization" not in request.headers  # unauthenticated call
        return httpx.Response(
            201,
            json={
                "token": "sess-new",
                "user": {"email": "cli@example.com"},
                "tenant": {"name": "cli's workspace"},
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(
        app,
        ["signup", "--email", "cli@example.com", "--password-stdin"],
        input="pw-at-least-8\n",
    )

    assert result.exit_code == 0, result.output
    assert config_store.get_token() == "sess-new"
    assert "cli's workspace" in result.stdout
    assert "was created for you automatically." in result.stdout


def test_login_wrong_password_is_generic_and_stores_no_token(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid email or password"})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(
        app,
        ["login", "--email", "cli@example.com", "--password-stdin"],
        input="wrong-password\n",
    )

    assert result.exit_code == 1
    assert "Incorrect email or password." in result.stderr
    assert config_store.get_token() is None


def test_logout_clears_token_and_is_fine_when_absent(config_env, monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.url.path == "/auth/logout"
        return httpx.Response(204)

    _stub_api(monkeypatch, handler)

    config_store.set_token("sess-live")
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0, result.output
    assert "Signed out." in result.stdout
    assert config_store.get_token() is None
    assert calls["n"] == 1

    # Idempotent: logging out again with no stored token still succeeds, no call.
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    assert "Signed out." in result.stdout
    assert calls["n"] == 1


def test_whoami_without_token_says_login_and_makes_no_call(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("whoami must not hit the API without a stored token")

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 1
    assert "vocky login" in result.stderr
    assert config_store.get_token() is None
