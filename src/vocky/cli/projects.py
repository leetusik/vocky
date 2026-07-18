"""Projects, credentials, and usage commands for the ``vocky`` CLI.

The session-authenticated ``/app/*`` control plane a signed-in user drives to set
up vocky: manage **projects**, mint/list/revoke per-project ``vk_`` **keys** (the
show-once credential a product backend uses to authenticate to ``/api/*`` +
``/mcp``), and see capture **usage**. Every command authenticates with the stored
session token via :meth:`CliContext.authed_client` — never the ``vk_`` key.

Follows the command-module shape (see :mod:`vocky.cli.auth`): define the bodies
here, group the sub-commands with ``typer.Typer()`` sub-apps, and expose a
:func:`register` that mounts them on the root app — importing only from
``context`` / ``config_store`` / ``client`` so registration from the bottom of
:mod:`vocky.cli.app` cannot form an import cycle.
"""

from __future__ import annotations

from typing import Any

import typer

from vocky.cli.context import CliContext, cli_errors

projects_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Manage the projects under your workspace.",
)
keys_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Mint, list, and revoke a project's `vk_` ingest keys.",
)

_PROJECT_OPTION = typer.Option(
    ...,
    "--project",
    metavar="PROJECT_ID",
    help="The project the key belongs to.",
)


def _date(timestamp: str | None) -> str:
    """Reduce an ISO-8601 timestamp to its date for compact list output."""

    if not timestamp:
        return "—"
    return timestamp[:10] if "T" in timestamp else timestamp


# --- projects -------------------------------------------------------------


def _projects_list(ctx: typer.Context) -> None:
    """List the projects under your workspace, oldest first."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            result = client.get("/app/projects")

        projects = result.get("projects") or []
        if not projects:
            typer.echo(
                "No projects yet. Create one with `vocky projects create <name>`."
            )
            return

        for project in projects:
            # The project id is the handle for `projects show` and every
            # `--project` consumer (keys, usage) — print it in full so the row is
            # copy-pasteable.
            typer.echo(
                f"{project['id']}  {project['name']}  "
                f"(created {_date(project.get('created_at'))})"
            )


def _projects_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., metavar="NAME", help="The project's name."),
) -> None:
    """Create a project under your workspace."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            result = client.post("/app/projects", json={"name": name})

        project = result["project"]
        typer.echo(f'Created project "{project["name"]}" ({project["id"]}).')


def _projects_show(
    ctx: typer.Context,
    project_id: str = typer.Argument(
        ..., metavar="PROJECT_ID", help="The project's id."
    ),
) -> None:
    """Show one project's id, name, and creation time."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            result = client.get(f"/app/projects/{project_id}")

        project = result["project"]
        typer.echo(f"id:         {project['id']}")
        typer.echo(f"name:       {project['name']}")
        typer.echo(f"created_at: {project.get('created_at')}")


# --- keys -----------------------------------------------------------------


def _keys_mint(
    ctx: typer.Context,
    project: str = _PROJECT_OPTION,
    name: str | None = typer.Option(
        None, "--name", metavar="LABEL", help="An optional display label for the key."
    ),
) -> None:
    """Mint a `vk_` ingest key for a project (shown once)."""

    with cli_errors():
        context: CliContext = ctx.obj
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        with context.authed_client() as client:
            result = client.post(
                f"/app/projects/{project}/credentials",
                json=body or None,
            )

        # The show-once contract: the plaintext key is returned only here and is
        # never recoverable — warn, then print it alone so it is easy to copy.
        typer.echo(
            "Copy this key now — it is shown only once and cannot be recovered. "
            "If you lose it, revoke it and mint a new one."
        )
        typer.echo(result["key"])


def _keys_list(
    ctx: typer.Context,
    project: str = _PROJECT_OPTION,
) -> None:
    """List a project's credentials (metadata only; never the key)."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            result = client.get(f"/app/projects/{project}/credentials")

        credentials = result.get("credentials") or []
        if not credentials:
            typer.echo(
                f"No keys yet. Mint one with `vocky keys mint --project {project}`."
            )
            return

        for credential in credentials:
            label = credential.get("name") or "—"
            last_used = credential.get("last_used_at")
            last_used_text = _date(last_used) if last_used else "never"
            state = "revoked" if credential.get("revoked_at") else "active"
            typer.echo(
                f"{credential['id']}  {credential['token_prefix']}…  {label}  "
                f"(created {_date(credential.get('created_at'))}, "
                f"last used {last_used_text}, {state})"
            )


def _keys_revoke(
    ctx: typer.Context,
    project: str = _PROJECT_OPTION,
    credential_id: str = typer.Argument(
        ..., metavar="CREDENTIAL_ID", help="The credential id to revoke."
    ),
) -> None:
    """Revoke (soft-delete) one of a project's keys."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            client.delete(f"/app/projects/{project}/credentials/{credential_id}")

        typer.echo(f"Revoked key {credential_id}.")


# --- usage ----------------------------------------------------------------


def _usage(
    ctx: typer.Context,
    project: str | None = typer.Option(
        None,
        "--project",
        metavar="PROJECT_ID",
        help="Scope usage to one project instead of the whole workspace.",
    ),
    start: str | None = typer.Option(
        None, "--start", metavar="ISO8601", help="Window start (ISO-8601)."
    ),
    end: str | None = typer.Option(
        None, "--end", metavar="ISO8601", help="Window end (ISO-8601)."
    ),
) -> None:
    """Show capture usage for your workspace or a single project."""

    with cli_errors():
        context: CliContext = ctx.obj
        params: dict[str, Any] = {}
        if start is not None:
            params["start_ingested_at"] = start
        if end is not None:
            params["end_ingested_at"] = end

        path = f"/app/projects/{project}/usage" if project else "/app/usage"
        with context.authed_client() as client:
            result = client.get(path, params=params or None)

        window = result.get("window") or {}
        typer.echo(
            f"Window: {window.get('start_ingested_at')} → "
            f"{window.get('end_ingested_at')}"
        )
        totals = result.get("totals") or {}
        typer.echo(
            f"Captured: {totals.get('total', 0)} total "
            f"({totals.get('liked', 0)} liked, "
            f"{totals.get('disliked', 0)} disliked, "
            f"{totals.get('unrated', 0)} unrated)"
        )

        if project:
            credentials = result.get("credentials") or []
            if credentials:
                typer.echo("Keys:")
                for credential in credentials:
                    last_used = credential.get("last_used_at")
                    last_used_text = _date(last_used) if last_used else "never"
                    typer.echo(
                        f"  {credential['token_prefix']}…  last used {last_used_text}"
                    )
        else:
            projects = result.get("projects") or []
            if projects:
                typer.echo("Projects:")
                for entry in projects:
                    # Full id — it's the `--project` handle for this same command.
                    typer.echo(f"  {entry['id']}  {entry['name']}")


def register(app: typer.Typer) -> None:
    """Mount the projects/keys groups and the usage command on the root app."""

    projects_app.command("list")(_projects_list)
    projects_app.command("create")(_projects_create)
    projects_app.command("show")(_projects_show)

    keys_app.command("mint")(_keys_mint)
    keys_app.command("list")(_keys_list)
    keys_app.command("revoke")(_keys_revoke)

    app.add_typer(projects_app, name="projects")
    app.add_typer(keys_app, name="keys")
    app.command("usage")(_usage)
