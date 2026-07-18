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
