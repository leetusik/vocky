"""Shared CLI helpers reused across every ``vocky`` command module.

Extracted from :mod:`vocky.cli.app` so command modules (auth, projects/keys/
usage, feedback) can import the per-invocation context, base-URL resolution, and
the error-to-stderr helpers **without** importing ``app`` — which in turn imports
those command modules to register them. Keeping these here breaks that cycle:
``context`` imports only ``config_store`` + ``client`` and nothing from ``app``
or any command module, so import order never matters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NoReturn

import typer

from vocky.cli import config_store
from vocky.cli.client import ApiClient, CliError

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass
class CliContext:
    """Per-invocation context stashed on ``ctx.obj`` for sub-commands.

    Carries the resolved base URL and exposes the config store plus a configured
    :class:`ApiClient` factory the command groups reuse.
    """

    base_url: str
    store = config_store  # the config-store module, for sub-commands

    def make_client(
        self, *, token: str | None = None, use_stored_token: bool = True
    ) -> ApiClient:
        """Build an :class:`ApiClient` for this invocation.

        Uses the explicit ``token`` when given; otherwise the stored session
        token unless ``use_stored_token`` is false (e.g. for signup/login, which
        must run unauthenticated).
        """

        effective_token = token
        if effective_token is None and use_stored_token:
            effective_token = config_store.get_token()
        return ApiClient(self.base_url, token=effective_token)

    def authed_client(self) -> ApiClient:
        """Build a session-authenticated client, requiring a stored token.

        The shared "must be signed in" seam for every ``/app/*`` command: when no
        session token is stored it fails up front with the friendly "run ``vocky
        login``" hint (a token-less request would otherwise 401 into a raw
        :class:`ApiError`). Otherwise it returns :meth:`make_client`, which injects
        the stored token.
        """

        if config_store.get_token() is None:
            fail("Not signed in — run `vocky login`.")
        return self.make_client()


def resolve_base_url(base_url_flag: str | None) -> str:
    """Resolve the API base URL by precedence.

    ``--base-url`` flag > ``VOCKY_BASE_URL`` env > stored config > the
    ``http://127.0.0.1:8000`` default. A trailing slash is stripped.
    """

    if base_url_flag:
        return base_url_flag.rstrip("/")

    env_base_url = os.environ.get("VOCKY_BASE_URL", "").strip()
    if env_base_url:
        return env_base_url.rstrip("/")

    stored_base_url = config_store.get_base_url()
    if stored_base_url:
        return stored_base_url.rstrip("/")

    return DEFAULT_BASE_URL


def resolve_api_token() -> str:
    """Resolve the ``vk_`` ingest key for ``vocky capture`` from its env var.

    Precedence is exactly one tier: ``VOCKY_API_TOKEN`` or nothing. There is
    **no** ``--token`` flag — the same reasoning ``auth.py`` already applies to
    ``--password`` (never ``--password-stdin``'s stdin path, but a bare flag):
    argv is world-readable via ``ps`` and lands in shell history, and a ``vk_``
    key is a bearer credential with the same exposure. There is also **no**
    config-store persistence — ``config_store`` holds only the session `token`
    and `clear_token()` only pops that key, so a persisted `vk_` key would
    silently survive `vocky logout`, a leak-shaped bug. Fails with a message
    naming the env var when it is unset or blank.
    """

    env_api_token = os.environ.get("VOCKY_API_TOKEN", "").strip()
    if env_api_token:
        return env_api_token

    fail(
        "VOCKY_API_TOKEN is not set — mint a key with `vocky keys mint` and "
        "export it."
    )


def fail(message: str) -> NoReturn:
    """Print ``message`` to stderr and exit non-zero."""

    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(1)


class cli_errors:
    """Context manager that turns a raised :class:`CliError` into a clean exit.

    Sub-commands wrap their bodies with ``with cli_errors():`` so a client error
    prints its message to stderr and exits non-zero instead of tracing back.
    """

    def __enter__(self) -> "cli_errors":
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if isinstance(exc, CliError):
            fail(exc.message)
        return False
