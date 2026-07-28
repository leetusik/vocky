"""Shared sync HTTP client for the ``vocky`` CLI.

A thin wrapper over ``httpx.Client`` (mirroring the sync-client pattern in
``vocky.smoke``) that injects ``Authorization: Bearer <token>`` and maps every
outcome onto a small, typed error contract the auth/projects/feedback command
groups (added in later slices) all reuse:

* a ``401`` on a request that **sent** a token -> :class:`CliError` telling the
  user to run ``vocky login`` (the session is expired/invalid);
* a ``401`` on an **unauthenticated** request (no token sent — e.g. login /
  signup) -> :class:`ApiError` carrying the status and the server ``detail`` so
  the command can surface it as "Incorrect email or password";
* other non-2xx -> :class:`ApiError` carrying the status and the server's
  ``{"detail": ...}`` (falling back to response text / status);
* a transport/connection failure -> :class:`CliError` naming the base URL.

Commands render a :class:`CliError` to stderr and exit non-zero (see
``vocky.cli.app.cli_errors``); the client never prints or calls ``sys.exit``.
"""

from __future__ import annotations

from typing import Any

import httpx

from vocky.smoke import make_http_user_agent

DEFAULT_TIMEOUT = 30.0


class CliError(Exception):
    """A user-facing CLI failure carrying a ready-to-print ``message``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ApiError(CliError):
    """A non-2xx API response, carrying the HTTP status and server detail."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    """Sync API client bound to one resolved base URL and optional token.

    Usable as a context manager (``with ApiClient(...) as client:``) so the
    underlying ``httpx.Client`` is closed. ``transport`` is injectable for tests
    (e.g. ``httpx.MockTransport``).
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"User-Agent": make_http_user_agent()},
            timeout=timeout,
            follow_redirects=False,
            transport=transport,
        )

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""

        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        token: str | None = None,
        json: Any = None,
        params: dict[str, Any] | None = None,
        unauthorized_message: str | None = None,
    ) -> Any:
        """Send a request and return parsed JSON (or ``None`` for empty bodies).

        Injects a Bearer header from ``token`` when given, else from the client's
        stored token when ``auth`` is true. Raises :class:`CliError` /
        :class:`ApiError` on failure — see the module docstring.

        ``unauthorized_message`` overrides the default "Not signed in — run
        `vocky login`." message a token-bearing ``401`` raises — for a caller
        whose token is not a session token (e.g. ``capture``'s ``vk_`` key),
        that default is actively wrong. It never changes any other outcome.
        """

        headers: dict[str, str] = {}
        effective_token = token if token is not None else (self.token if auth else None)
        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"

        try:
            response = self._client.request(
                method,
                path,
                headers=headers or None,
                json=json,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise CliError(
                f"Could not reach vocky at {self.base_url} ({exc})."
            ) from exc

        return self._handle(
            response,
            token_sent=bool(effective_token),
            unauthorized_message=unauthorized_message,
        )

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    @staticmethod
    def _handle(
        response: httpx.Response,
        *,
        token_sent: bool,
        unauthorized_message: str | None = None,
    ) -> Any:
        if response.is_success:
            if response.status_code == 204 or not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                return None

        # A 401 on an authenticated request means the session is expired/invalid
        # — steer the user to re-login. A 401 on a request that sent no token
        # (login/signup) is a credential rejection: surface the server detail so
        # the command can render "Incorrect email or password". A caller may
        # override the message (e.g. `capture`'s `vk_` key isn't a session).
        if response.status_code == 401 and token_sent:
            raise CliError(unauthorized_message or "Not signed in — run `vocky login`.")

        raise ApiError(response.status_code, ApiClient._extract_detail(response))

    @staticmethod
    def _extract_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str) and detail:
                return detail

        text = response.text.strip()
        return text or f"HTTP {response.status_code}"
