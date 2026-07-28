"""Root Typer app for the ``vocky`` CLI.

Builds the CLI spine every command group reuses: global ``--version`` and
``--base-url`` handling, base-URL resolution, and a small per-invocation context
on ``ctx.obj``. The shared context helpers (:class:`CliContext`,
:func:`resolve_base_url`, :func:`fail`, :class:`cli_errors`, ``DEFAULT_BASE_URL``)
live in :mod:`vocky.cli.context` so command modules can reuse them without an
``app`` ↔ command-module import cycle; they are re-exported here for callers (and
tests) that reach for ``vocky.cli.app.DEFAULT_BASE_URL`` / ``resolve_base_url``.

Command modules register their top-level commands at the bottom of this file via
``<module>.register(app)`` — auth here, projects/keys/usage and feedback in later
slices.
"""

from __future__ import annotations

from importlib.metadata import version as package_version

import typer

from vocky.cli.context import (
    DEFAULT_BASE_URL,
    CliContext,
    cli_errors,
    fail,
    resolve_base_url,
)

__all__ = [
    "app",
    "main",
    "DEFAULT_BASE_URL",
    "CliContext",
    "cli_errors",
    "fail",
    "resolve_base_url",
]

app = typer.Typer(
    name="vocky",
    no_args_is_help=True,
    add_completion=False,
    help=(
        "vocky CLI — sign up, log in, manage projects and keys, and read "
        "feedback from your terminal, without visiting the website."
    ),
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(package_version("vocky"))
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        metavar="URL",
        help="vocky API base URL (overrides VOCKY_BASE_URL and stored config).",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        is_eager=True,
        callback=_version_callback,
        help="Show the vocky version and exit.",
    ),
) -> None:
    """Resolve the base URL and stash the shared context for sub-commands."""

    ctx.obj = CliContext(base_url=resolve_base_url(base_url))


def main() -> None:
    """Console-script entry point for the ``vocky`` command."""

    app()


# Register command modules on the root app. Each module exposes ``register(app)``
# and imports only from ``context`` / ``config_store`` / ``client`` — never from
# this module — so this bottom-of-file wiring cannot form an import cycle.
from vocky.cli import auth  # noqa: E402  (import after ``app`` exists)
from vocky.cli import capture  # noqa: E402  (import after ``app`` exists)
from vocky.cli import feedback  # noqa: E402  (import after ``app`` exists)
from vocky.cli import projects  # noqa: E402  (import after ``app`` exists)

auth.register(app)
capture.register(app)
projects.register(app)
feedback.register(app)


if __name__ == "__main__":
    main()
