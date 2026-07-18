"""Feedback read-command tests for the ``vocky`` CLI.

Terse, high-value cases only — no live server. Drives the Typer app through
``CliRunner`` with the ``/app/feedback`` API stubbed by ``httpx.MockTransport``
(injected by patching the client factory) and the config store pointed at a
throwaway ``VOCKY_CONFIG_DIR`` with a token pre-stored so ``authed_client``
passes.
"""

from __future__ import annotations

import httpx
import pytest
from typer.testing import CliRunner

from vocky.cli import config_store
from vocky.cli.app import app
from vocky.cli.client import ApiClient
from vocky.cli.context import CliContext

runner = CliRunner()

FEEDBACK_ID = "22222222-2222-2222-2222-222222222222"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"


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


def test_list_renders_row_and_cursor_hint(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/feedback"
        assert request.headers["Authorization"] == "Bearer sess-live"
        return httpx.Response(
            200,
            json={
                "records": [
                    {
                        "id": FEEDBACK_ID,
                        "message": "checkout keeps failing",
                        "feedback_value": 2,
                        "project_id": PROJECT_ID,
                        "ingested_at": "2026-07-18T09:00:00Z",
                    }
                ],
                "next_cursor": "opaque-cursor",
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["feedback", "list"])

    assert result.exit_code == 0, result.output
    # The feedback id must be the full UUID (the handle `feedback show` needs),
    # not an 8-char prefix.
    assert FEEDBACK_ID in result.stdout
    assert "dislike" in result.stdout
    assert "checkout keeps failing" in result.stdout
    assert "--cursor opaque-cursor" in result.stdout


def test_list_empty_shows_hint(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/feedback"
        return httpx.Response(200, json={"records": []})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["feedback", "list"])

    assert result.exit_code == 0, result.output
    assert "No feedback yet." in result.stdout


def test_search_round_trips_korean_query(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/feedback"
        assert request.url.params.get("q") == "결제"
        return httpx.Response(
            200,
            json={
                "records": [
                    {
                        "id": FEEDBACK_ID,
                        "message": "결제가 안 돼요",
                        "feedback_value": None,
                        "project_id": PROJECT_ID,
                        "ingested_at": "2026-07-18T09:00:00Z",
                    }
                ]
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["feedback", "search", "결제"])

    assert result.exit_code == 0, result.output
    assert "결제가 안 돼요" in result.stdout


def test_show_renders_message_comment_and_attachment(config_env, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/app/feedback/{FEEDBACK_ID}"
        return httpx.Response(
            200,
            json={
                "record": {
                    "id": FEEDBACK_ID,
                    "project_id": PROJECT_ID,
                    "message": "the export button is broken",
                    "feedback_value": 2,
                    "source_product": "acme-app",
                    "channel": "web",
                    "tags": ["bug"],
                    "ingested_at": "2026-07-18T09:00:00Z",
                    "comments": [
                        {"author": "sam", "body": "reproduced, filing a ticket"}
                    ],
                    "attachments": [
                        {
                            "filename": "screenshot.png",
                            "url": f"/app/feedback/{FEEDBACK_ID}/attachments/a1",
                        }
                    ],
                }
            },
        )

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["feedback", "show", FEEDBACK_ID])

    assert result.exit_code == 0, result.output
    assert "the export button is broken" in result.stdout
    assert "[sam] reproduced, filing a ticket" in result.stdout
    assert "screenshot.png" in result.stdout


def test_list_id_round_trips_into_show(config_env, monkeypatch):
    """The id `feedback list` prints is the full UUID `feedback show` consumes."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/app/feedback":
            return httpx.Response(
                200,
                json={
                    "records": [
                        {
                            "id": FEEDBACK_ID,
                            "message": "checkout keeps failing",
                            "feedback_value": 2,
                            "project_id": PROJECT_ID,
                            "ingested_at": "2026-07-18T09:00:00Z",
                        }
                    ]
                },
            )
        assert request.url.path == f"/app/feedback/{FEEDBACK_ID}"
        return httpx.Response(
            200,
            json={
                "record": {
                    "id": FEEDBACK_ID,
                    "project_id": PROJECT_ID,
                    "message": "checkout keeps failing",
                    "feedback_value": 2,
                    "ingested_at": "2026-07-18T09:00:00Z",
                }
            },
        )

    _stub_api(monkeypatch, handler)
    listed = runner.invoke(app, ["feedback", "list"])
    assert listed.exit_code == 0, listed.output

    printed_id = listed.stdout.split()[0]
    assert printed_id == FEEDBACK_ID  # full id, copy-pasteable

    shown = runner.invoke(app, ["feedback", "show", printed_id])
    assert shown.exit_code == 0, shown.output
    assert "checkout keeps failing" in shown.stdout


def test_show_maps_invalid_id_to_friendly_hint(config_env, monkeypatch):
    """A raw UUID-400 from the server becomes a hint pointing at `feedback list`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "feedback_id must be a valid UUID"})

    _stub_api(monkeypatch, handler)
    result = runner.invoke(app, ["feedback", "show", "not-a-uuid"])

    assert result.exit_code == 1
    assert "not a valid feedback id" in result.stderr
    assert "vocky feedback list" in result.stderr
