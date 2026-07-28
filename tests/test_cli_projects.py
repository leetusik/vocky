"""Projects/keys/usage command tests for the ``vocky`` CLI.

Terse, high-value cases only — no live server. Drives the Typer app through
``CliRunner`` with the ``/app/*`` API stubbed by ``httpx.MockTransport`` (injected
by patching the client factory) and the config store pointed at a throwaway
``VOCKY_CONFIG_DIR`` with a token pre-stored so ``authed_client`` passes.
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
    """Point the config store at a throwaway dir with a session token stored."""

    monkeypatch.setenv("VOCKY_CONFIG_DIR", str(tmp_path / "vocky"))
    monkeypatch.delenv("VOCKY_BASE_URL", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
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


def test_projects_create_reports_id_and_name(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/app/projects"
        assert json.loads(request.content) == {"name": "foo"}
        assert request.headers["Authorization"] == "Bearer sess-live"
        return httpx.Response(
            201,
            json={
                "project": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "name": "foo",
                    "tenant_id": "t",
                    "created_at": "2026-07-18T00:00:00+00:00",
                }
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["projects", "create", "foo"])

    assert result.exit_code == 0, result.output
    assert 'Created project "foo"' in result.stdout
    assert "11111111-1111-1111-1111-111111111111" in result.stdout


def test_projects_list_prints_full_id(config_env, monkeypatch):
    """`projects list` prints the full id so `show` / `--project` are reachable."""

    project_id = "11111111-1111-1111-1111-111111111111"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/projects"
        return httpx.Response(
            200,
            json={
                "projects": [
                    {
                        "id": project_id,
                        "name": "foo",
                        "created_at": "2026-07-18T00:00:00+00:00",
                    }
                ]
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0, result.output
    assert result.stdout.split()[0] == project_id  # full id, copy-pasteable


def test_projects_list_empty_shows_hint(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/projects"
        return httpx.Response(200, json={"projects": []})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 0, result.output
    assert "No projects yet." in result.stdout


def test_keys_mint_prints_key_once_with_warning(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/app/projects/p1/credentials"
        return httpx.Response(
            201,
            json={
                "credential": {
                    "id": "c1",
                    "project_id": "p1",
                    "token_prefix": "vk_abcd1234",
                    "name": "backend",
                },
                "key": "vk_abcd1234secretsecret",
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(
        app, ["keys", "mint", "--project", "p1", "--name", "backend"]
    )

    assert result.exit_code == 0, result.output
    assert "shown only once" in result.stdout
    # The plaintext key must remain the last line — a contract coding agents
    # parse against (docs/cli.md).
    assert result.stdout.rstrip("\n").splitlines()[-1] == "vk_abcd1234secretsecret"


def test_keys_mint_without_project_hits_org_route_and_shows_scope(
    config_env, monkeypatch
):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/app/credentials"
        return httpx.Response(
            201,
            json={
                "credential": {
                    "id": "c2",
                    "project_id": None,
                    "token_prefix": "vk_orgorg1",
                    "name": None,
                },
                "key": "vk_orgorg1secretsecret",
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "mint"])

    assert result.exit_code == 0, result.output
    assert "org" in result.stdout
    assert result.stdout.rstrip("\n").splitlines()[-1] == "vk_orgorg1secretsecret"


def test_keys_list_renders_org_and_project_scoped_rows(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/app/credentials"
        return httpx.Response(
            200,
            json={
                "credentials": [
                    {
                        "id": "c-org",
                        "project_id": None,
                        "name": "ci",
                        "token_prefix": "vk_orgorg1",
                        "created_at": "2026-07-18T00:00:00+00:00",
                        "last_used_at": None,
                        "revoked_at": None,
                    },
                    {
                        "id": "c-proj",
                        "project_id": "p1",
                        "name": "backend",
                        "token_prefix": "vk_abcd1234",
                        "created_at": "2026-07-18T00:00:00+00:00",
                        "last_used_at": None,
                        "revoked_at": None,
                    },
                ]
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "list"])

    assert result.exit_code == 0, result.output
    assert "org" in result.stdout
    assert "project" in result.stdout


def test_keys_list_empty_org_hint_names_project_scoped_command(
    config_env, monkeypatch
):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/credentials"
        return httpx.Response(200, json={"credentials": []})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "list"])

    assert result.exit_code == 0, result.output
    assert "--project None" not in result.stdout
    assert "--project" in result.stdout


def test_keys_revoke_confirms(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/app/projects/p1/credentials/c1"
        return httpx.Response(204)

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "revoke", "--project", "p1", "c1"])

    assert result.exit_code == 0, result.output
    assert "Revoked key c1." in result.stdout


def test_keys_revoke_without_project_hits_org_route(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/app/credentials/c2"
        return httpx.Response(204)

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "revoke", "c2"])

    assert result.exit_code == 0, result.output
    assert "Revoked key c2." in result.stdout


def test_keys_revoke_without_project_translates_malformed_id(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/credentials/not-a-uuid"
        return httpx.Response(400, json={"detail": "credential_id must be a valid UUID"})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["keys", "revoke", "not-a-uuid"])

    assert result.exit_code == 1
    assert "not a valid credential id" in result.stderr
    assert "vocky keys list" in result.stderr


def test_no_token_says_login_and_makes_no_call(tmp_path, monkeypatch):
    monkeypatch.setenv("VOCKY_CONFIG_DIR", str(tmp_path / "vocky"))
    monkeypatch.delenv("VOCKY_BASE_URL", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("must not hit the API without a stored token")

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["projects", "list"])

    assert result.exit_code == 1
    assert "vocky login" in result.stderr
