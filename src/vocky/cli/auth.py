"""Auth commands for the ``vocky`` CLI: ``signup`` / ``login`` / ``logout`` /
``whoami``.

Top-level commands driving the public ``/auth/*`` surface and the on-disk
session token (via :mod:`vocky.cli.config_store`). This is the entry point of the
whole onboarding flow — an agent can sign a user up and in headlessly by piping
the password through ``--password-stdin`` (never on argv).

Command modules follow one shape: define the command bodies here, expose a
:func:`register` that binds them onto the root app, and import only from
``context`` / ``config_store`` / ``client`` (never from ``app``) so registration
from the bottom of :mod:`vocky.cli.app` cannot form an import cycle.
"""

from __future__ import annotations

import sys

import typer

from vocky.cli import config_store
from vocky.cli.client import ApiError
from vocky.cli.context import CliContext, cli_errors, fail

_EMAIL_OPTION = typer.Option(
    None, "--email", metavar="EMAIL", help="Account email (prompted if omitted)."
)
_PASSWORD_STDIN_OPTION = typer.Option(
    False,
    "--password-stdin",
    help="Read the password from one line of stdin (non-interactive / agent use).",
)


def _read_credentials(
    email: str | None, password_stdin: bool, *, confirm: bool
) -> tuple[str, str]:
    """Resolve the email + password for a signup/login call.

    Email comes from ``--email`` or an interactive prompt. The password is read
    from a single line of stdin when ``--password-stdin`` is set (so an agent
    never places it on argv), otherwise from a hidden prompt (confirmed on
    signup). The password is never echoed.
    """

    email_value = (email if email is not None else typer.prompt("Email")).strip()
    if not email_value:
        fail("An email is required.")

    if password_stdin:
        password_value = sys.stdin.readline().rstrip("\r\n")
        if not password_value:
            fail("No password on stdin — pipe one line to --password-stdin.")
    else:
        password_value = typer.prompt(
            "Password", hide_input=True, confirmation_prompt=confirm
        )

    return email_value, password_value


def _signup(
    ctx: typer.Context,
    email: str | None = _EMAIL_OPTION,
    password_stdin: bool = _PASSWORD_STDIN_OPTION,
) -> None:
    """Create an account (and its auto-provisioned workspace) and sign in."""

    with cli_errors():
        context: CliContext = ctx.obj
        email_value, password_value = _read_credentials(
            email, password_stdin, confirm=True
        )
        with context.make_client(use_stored_token=False) as client:
            try:
                result = client.post(
                    "/auth/signup",
                    json={"email": email_value, "password": password_value},
                    auth=False,
                )
            except ApiError as exc:
                if exc.status_code == 409:
                    fail(
                        "An account with that email already exists — "
                        "run `vocky login`."
                    )
                raise  # 400 (e.g. password < 8) surfaces the server detail.

        config_store.set_token(result["token"])
        typer.echo(f"Signed up and signed in as {result['user']['email']}.")
        typer.echo(
            f'A workspace "{result["tenant"]["name"]}" '
            "was created for you automatically."
        )


def _login(
    ctx: typer.Context,
    email: str | None = _EMAIL_OPTION,
    password_stdin: bool = _PASSWORD_STDIN_OPTION,
) -> None:
    """Sign in to an existing account and store the session token."""

    with cli_errors():
        context: CliContext = ctx.obj
        email_value, password_value = _read_credentials(
            email, password_stdin, confirm=False
        )
        with context.make_client(use_stored_token=False) as client:
            try:
                result = client.post(
                    "/auth/login",
                    json={"email": email_value, "password": password_value},
                    auth=False,
                )
            except ApiError as exc:
                if exc.status_code == 401:
                    # Generic on purpose — never enumerate which half was wrong.
                    fail("Incorrect email or password.")
                raise

        config_store.set_token(result["token"])
        typer.echo(f"Signed in as {result['user']['email']}.")


def _logout(ctx: typer.Context) -> None:
    """Sign out: best-effort server revoke, then drop the local token."""

    with cli_errors():
        context: CliContext = ctx.obj
        token = config_store.get_token()
        if token is not None:
            try:
                with context.make_client() as client:
                    client.post("/auth/logout")
            except Exception:  # noqa: BLE001 — best-effort; logout is idempotent.
                pass
        config_store.clear_token()
        typer.echo("Signed out.")


def _whoami(ctx: typer.Context) -> None:
    """Show the signed-in account and its workspace(s)."""

    with cli_errors():
        context: CliContext = ctx.obj
        if config_store.get_token() is None:
            fail("Not signed in — run `vocky login`.")

        with context.make_client() as client:
            result = client.get("/auth/me")

        typer.echo(f"Signed in as {result['user']['email']}.")
        tenants = result.get("tenants") or []
        if tenants:
            names = ", ".join(str(tenant["name"]) for tenant in tenants)
            label = "Workspace" if len(tenants) == 1 else "Workspaces"
            typer.echo(f"{label}: {names}")


def register(app: typer.Typer) -> None:
    """Bind the auth commands as top-level commands on the root app."""

    app.command("signup")(_signup)
    app.command("login")(_login)
    app.command("logout")(_logout)
    app.command("whoami")(_whoami)
