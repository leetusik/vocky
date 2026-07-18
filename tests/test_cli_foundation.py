"""CLI foundation tests: config store, base-URL precedence, client error mapping.

Terse, high-value cases only — no server, no database. Covers the pieces the
later CLI slices reuse: the on-disk store round-trip + 0600 perms +
``VOCKY_CONFIG_DIR`` override, base-URL resolution precedence, and the shared
client's Bearer injection + 401 / detail error mapping via
``httpx.MockTransport``.
"""

from __future__ import annotations

import json
import stat

import httpx
import pytest

from vocky.cli import config_store
from vocky.cli.app import DEFAULT_BASE_URL, resolve_base_url
from vocky.cli.client import ApiClient, ApiError, CliError


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """Point the config store at a throwaway dir; never touch the real ~."""

    config_dir = tmp_path / "vocky"
    monkeypatch.setenv("VOCKY_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("VOCKY_BASE_URL", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return config_dir


def test_config_store_round_trip_and_perms(config_env):
    config_store.set_base_url("https://api.example.com")
    config_store.set_token("sess-token-123")

    # VOCKY_CONFIG_DIR override honored + values round-trip.
    assert config_store.config_dir() == config_env
    assert config_store.get_base_url() == "https://api.example.com"
    assert config_store.get_token() == "sess-token-123"

    path = config_store.config_path()
    assert path.parent == config_env
    assert json.loads(path.read_text()) == {
        "base_url": "https://api.example.com",
        "token": "sess-token-123",
    }
    # Tight perms: file 0600, dir 0700.
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(config_env.stat().st_mode) == 0o700

    # Clearing the token leaves the base URL intact.
    config_store.clear_token()
    assert config_store.get_token() is None
    assert config_store.get_base_url() == "https://api.example.com"


def test_base_url_precedence(config_env, monkeypatch):
    # Default when nothing is set.
    assert resolve_base_url(None) == DEFAULT_BASE_URL

    # Stored config beats the default.
    config_store.set_base_url("https://stored.example.com")
    assert resolve_base_url(None) == "https://stored.example.com"

    # Env beats stored.
    monkeypatch.setenv("VOCKY_BASE_URL", "https://env.example.com")
    assert resolve_base_url(None) == "https://env.example.com"

    # Flag beats env (trailing slash stripped).
    assert resolve_base_url("https://flag.example.com/") == "https://flag.example.com"


def _client(handler, *, token=None):
    return ApiClient("http://test", token=token, transport=httpx.MockTransport(handler))


def test_client_injects_bearer_and_parses_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"ok": True})

    with _client(handler, token="sess") as client:
        assert client.get("/auth/me") == {"ok": True}
    assert seen["auth"] == "Bearer sess"


def test_client_401_maps_to_login_hint():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "invalid email or password"})

    with _client(handler, token="stale") as client:
        with pytest.raises(CliError) as excinfo:
            client.get("/app/tenant")

    # 401 is the generic "run login" hint, not a detail-bearing ApiError.
    assert not isinstance(excinfo.value, ApiError)
    assert "vocky login" in excinfo.value.message


def test_client_surfaces_detail_on_400():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "name too long"})

    with _client(handler) as client:
        with pytest.raises(ApiError) as excinfo:
            client.post("/app/projects", json={"name": "x"})

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "name too long"
    assert "name too long" in excinfo.value.message
