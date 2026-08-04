"""Account auth REST tests (`/auth/signup|login|logout|me`)."""

from __future__ import annotations

import json

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request

from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.auth_api import routes as auth_routes
from vocky.config import get_settings
from vocky.rate_limit import client_ip


def make_auth_app() -> Starlette:
    """Create a test app with just the auth routes and the 401 handler."""

    return Starlette(
        routes=auth_routes,
        exception_handlers={AuthError: auth_error_handler},
    )


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=make_auth_app())
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _assert_no_secrets(body: object) -> None:
    dumped = json.dumps(body)
    assert "password_hash" not in dumped
    assert "token_hash" not in dumped


@pytest.mark.anyio
async def test_signup_creates_user_tenant_and_token(configured_database: str) -> None:
    async with _client() as client:
        response = await client.post(
            "/auth/signup",
            json={"email": "Alice@Example.com ", "password": "hunter2pass"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["tenant"]["name"] == "alice's workspace"
    # Additive since P10.S1: signup also provisions the org's "default" project.
    assert body["project"]["name"] == "default"
    assert body["project"]["tenant_id"] == body["tenant"]["id"]
    _assert_no_secrets(body)


@pytest.mark.anyio
async def test_signup_duplicate_email_returns_409(configured_database: str) -> None:
    async with _client() as client:
        first = await client.post(
            "/auth/signup", json={"email": "dup@example.com", "password": "hunter2pass"}
        )
        second = await client.post(
            "/auth/signup", json={"email": "dup@example.com", "password": "otherpass1"}
        )

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.anyio
async def test_signup_rejects_short_password_and_bad_email(
    configured_database: str,
) -> None:
    async with _client() as client:
        short = await client.post(
            "/auth/signup", json={"email": "x@example.com", "password": "short"}
        )
        no_at = await client.post(
            "/auth/signup", json={"email": "nope", "password": "hunter2pass"}
        )

    assert short.status_code == 400
    assert no_at.status_code == 400


@pytest.mark.anyio
async def test_login_ok_and_generic_401(configured_database: str) -> None:
    async with _client() as client:
        await client.post(
            "/auth/signup", json={"email": "bob@example.com", "password": "hunter2pass"}
        )

        ok = await client.post(
            "/auth/login", json={"email": "bob@example.com", "password": "hunter2pass"}
        )
        wrong_password = await client.post(
            "/auth/login", json={"email": "bob@example.com", "password": "wrongpass1"}
        )
        unknown_email = await client.post(
            "/auth/login", json={"email": "ghost@example.com", "password": "hunter2pass"}
        )

    assert ok.status_code == 200
    assert ok.json()["token"]
    _assert_no_secrets(ok.json())

    # Identical generic 401 for unknown email vs wrong password (no enumeration).
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


@pytest.mark.anyio
async def test_me_requires_and_accepts_token(configured_database: str) -> None:
    async with _client() as client:
        signup = await client.post(
            "/auth/signup", json={"email": "carol@example.com", "password": "hunter2pass"}
        )
        token = signup.json()["token"]

        without = await client.get("/auth/me")
        with_token = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

    assert without.status_code == 401
    assert without.json() == {"detail": "Unauthorized"}
    assert without.headers["www-authenticate"] == "Bearer"

    assert with_token.status_code == 200
    body = with_token.json()
    assert body["user"]["email"] == "carol@example.com"
    assert len(body["tenants"]) == 1
    _assert_no_secrets(body)


@pytest.mark.anyio
async def test_logout_revokes_token(configured_database: str) -> None:
    async with _client() as client:
        signup = await client.post(
            "/auth/signup", json={"email": "dave@example.com", "password": "hunter2pass"}
        )
        token = signup.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        before = await client.get("/auth/me", headers=headers)
        logout = await client.post("/auth/logout", headers=headers)
        after = await client.get("/auth/me", headers=headers)
        # Idempotent: logging out an already-revoked token still succeeds.
        again = await client.post("/auth/logout", headers=headers)

    assert before.status_code == 200
    assert logout.status_code == 204
    assert after.status_code == 401
    assert again.status_code == 204


# --- rate limiting (P12.S3) ------------------------------------------------


@pytest.mark.anyio
async def test_rate_limit_trips_and_reports(
    configured_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOCKY_AUTH_RATE_LIMIT", "2")
    monkeypatch.setenv("VOCKY_AUTH_RATE_WINDOW_S", "60")
    get_settings.cache_clear()
    try:
        async with _client() as client:
            login_body = {"email": "nobody@example.com", "password": "wrongpass1"}
            first = await client.post("/auth/login", json=login_body)
            second = await client.post("/auth/login", json=login_body)
            third = await client.post("/auth/login", json=login_body)
    finally:
        get_settings.cache_clear()

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.json() == {"detail": "too many requests — please retry later"}
    assert 0 < int(third.headers["retry-after"]) <= 60


@pytest.mark.anyio
async def test_rate_limit_reads_forwarded_ip_not_the_shared_peer(
    configured_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worst failure mode: every client sharing one bucket.

    `httpx.ASGITransport` gives every client the same fixed peer address, so
    this only passes if the limiter genuinely reads `X-Real-IP` instead of
    (or in addition to) the socket peer.
    """

    monkeypatch.setenv("VOCKY_AUTH_RATE_LIMIT", "1")
    monkeypatch.setenv("VOCKY_AUTH_RATE_WINDOW_S", "60")
    get_settings.cache_clear()
    try:
        login_body = {"email": "nobody@example.com", "password": "wrongpass1"}
        async with _client() as first_client:
            first_allowed = await first_client.post("/auth/login", json=login_body)
            first_throttled = await first_client.post("/auth/login", json=login_body)
        async with _client() as second_client:
            second_allowed = await second_client.post(
                "/auth/login",
                json=login_body,
                headers={"X-Real-IP": "203.0.113.9"},
            )
    finally:
        get_settings.cache_clear()

    assert first_allowed.status_code == 401
    assert first_throttled.status_code == 429
    # A distinct forwarded IP is a distinct bucket, even though the ASGI peer
    # address (which httpx fixes) is identical for both clients.
    assert second_allowed.status_code == 401


@pytest.mark.anyio
async def test_rate_limit_is_per_route(
    configured_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOCKY_AUTH_RATE_LIMIT", "1")
    monkeypatch.setenv("VOCKY_AUTH_RATE_WINDOW_S", "60")
    get_settings.cache_clear()
    try:
        async with _client() as client:
            signup_allowed = await client.post(
                "/auth/signup",
                json={"email": "route-a@example.com", "password": "hunter2pass"},
            )
            signup_throttled = await client.post(
                "/auth/signup",
                json={"email": "route-b@example.com", "password": "hunter2pass"},
            )
            login_still_allowed = await client.post(
                "/auth/login",
                json={"email": "route-a@example.com", "password": "hunter2pass"},
            )
    finally:
        get_settings.cache_clear()

    assert signup_allowed.status_code == 201
    assert signup_throttled.status_code == 429
    assert login_still_allowed.status_code == 200


@pytest.mark.anyio
async def test_rate_limit_disabled_by_non_positive_limit(
    configured_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOCKY_AUTH_RATE_LIMIT", "0")
    get_settings.cache_clear()
    try:
        async with _client() as client:
            login_body = {"email": "nobody@example.com", "password": "wrongpass1"}
            responses = [await client.post("/auth/login", json=login_body) for _ in range(5)]
    finally:
        get_settings.cache_clear()

    assert all(response.status_code == 401 for response in responses)


def _make_request(
    headers: list[tuple[bytes, bytes]], peer: tuple[str, int] | None
) -> Request:
    return Request({"type": "http", "headers": headers, "client": peer})


def test_client_ip_header_precedence() -> None:
    real_ip = _make_request([(b"x-real-ip", b"203.0.113.5")], ("10.0.0.9", 1))
    assert client_ip(real_ip) == "203.0.113.5"

    forwarded = _make_request(
        [(b"x-forwarded-for", b"198.51.100.7, 10.0.0.1")], ("10.0.0.9", 1)
    )
    assert client_ip(forwarded) == "198.51.100.7"

    peer_only = _make_request([], ("10.0.0.9", 1))
    assert client_ip(peer_only) == "10.0.0.9"

    no_client = _make_request([], None)
    assert client_ip(no_client) == "unknown"
