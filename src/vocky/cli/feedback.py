"""Cross-project feedback read commands for the ``vocky`` CLI.

The session-authenticated ``/app/feedback`` surface a signed-in user drives to
**find and read** feedback across **all their projects** from the terminal —
list, Korean-safe substring search, and read-one (with operator comments and
attachments). It is **read-only**: management verbs (edit/delete/comment) live on
the ``vk_``-keyed ``/api/project/feedback`` surface and are out of scope here.

Follows the command-module shape (see :mod:`vocky.cli.projects`): define the
bodies here, group them under a ``typer.Typer()`` sub-app, and expose a
:func:`register` that mounts them on the root app — importing only from
``context`` / ``config_store`` / ``client`` so registration from the bottom of
:mod:`vocky.cli.app` cannot form an import cycle. Every command authenticates
with the stored session token via :meth:`CliContext.authed_client`.
"""

from __future__ import annotations

from typing import Any

import typer

from vocky.cli.context import CliContext, cli_errors

feedback_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Read and search feedback across your workspace's projects.",
)

_MESSAGE_WIDTH = 60

_PROJECT_OPTION = typer.Option(
    None,
    "--project",
    metavar="PROJECT_ID",
    help="Narrow to one owned project instead of the whole workspace.",
)
_LIMIT_OPTION = typer.Option(
    None,
    "--limit",
    metavar="N",
    help="Max records to return (the server caps at 100).",
)
_CURSOR_OPTION = typer.Option(
    None,
    "--cursor",
    metavar="CURSOR",
    help="Keyset cursor from a prior page's `— more` hint.",
)


def _short(identifier: str) -> str:
    """Return a short, glanceable prefix of a UUID for list output."""

    return identifier[:8]


def _date(timestamp: str | None) -> str:
    """Reduce an ISO-8601 timestamp to its date for compact list output."""

    if not timestamp:
        return "—"
    return timestamp[:10] if "T" in timestamp else timestamp


def _value_marker(value: Any) -> str:
    """Render a compact like/dislike marker for a list row (``·`` when unrated)."""

    return {1: "like", 2: "dislike"}.get(value, "·")


def _value_word(value: Any) -> str:
    """Render the feedback value for the detail view (``none`` when unrated)."""

    return {1: "like", 2: "dislike"}.get(value, "none")


def _truncate(text: str | None) -> str:
    """Collapse a message to one line, truncated to ~60 code points (Korean-safe)."""

    collapsed = " ".join((text or "").split())
    if len(collapsed) <= _MESSAGE_WIDTH:
        return collapsed
    return collapsed[: _MESSAGE_WIDTH - 1] + "…"


def _list_params(
    *, project: str | None, limit: int | None, cursor: str | None
) -> dict[str, Any]:
    """Build the shared ``/app/feedback`` query params for list and search."""

    params: dict[str, Any] = {}
    if project is not None:
        params["project_id"] = project
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    return params


def _render_records(records: list[dict[str, Any]]) -> None:
    """Print one compact row per feedback record, newest-first as returned."""

    for record in records:
        marker = _value_marker(record.get("feedback_value"))
        project_id = record.get("project_id")
        project_short = _short(str(project_id)) if project_id else "—"
        typer.echo(
            f"{_short(str(record['id']))}  {marker:<7}  {project_short}  "
            f"{_date(record.get('ingested_at'))}  {_truncate(record.get('message'))}"
        )


def _render_cursor_hint(result: dict[str, Any]) -> None:
    """Print the paging hint when the server returned a ``next_cursor``."""

    next_cursor = result.get("next_cursor")
    if next_cursor:
        typer.echo(f"— more: rerun with --cursor {next_cursor}")


def _feedback_list(
    ctx: typer.Context,
    project: str | None = _PROJECT_OPTION,
    limit: int | None = _LIMIT_OPTION,
    cursor: str | None = _CURSOR_OPTION,
) -> None:
    """List feedback across your workspace's projects, newest first."""

    with cli_errors():
        context: CliContext = ctx.obj
        params = _list_params(project=project, limit=limit, cursor=cursor)
        with context.authed_client() as client:
            result = client.get("/app/feedback", params=params or None)

        records = result.get("records") or []
        if not records:
            typer.echo("No feedback yet.")
            return

        _render_records(records)
        _render_cursor_hint(result)


def _feedback_search(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., metavar="QUERY", help="Substring to match in the message (Korean-safe)."
    ),
    project: str | None = _PROJECT_OPTION,
    limit: int | None = _LIMIT_OPTION,
    cursor: str | None = _CURSOR_OPTION,
) -> None:
    """Search feedback messages across your projects (case-insensitive substring)."""

    with cli_errors():
        context: CliContext = ctx.obj
        params = _list_params(project=project, limit=limit, cursor=cursor)
        params["q"] = query
        with context.authed_client() as client:
            result = client.get("/app/feedback", params=params)

        records = result.get("records") or []
        if not records:
            typer.echo(f'No feedback matches "{query}".')
            return

        _render_records(records)
        _render_cursor_hint(result)


def _feedback_show(
    ctx: typer.Context,
    feedback_id: str = typer.Argument(
        ..., metavar="FEEDBACK_ID", help="The feedback record's id."
    ),
) -> None:
    """Show one feedback record in full, with operator comments and attachments."""

    with cli_errors():
        context: CliContext = ctx.obj
        with context.authed_client() as client:
            result = client.get(f"/app/feedback/{feedback_id}")

        record = result["record"]
        typer.echo(f"id:          {record['id']}")
        typer.echo(f"project:     {record.get('project_id') or '—'}")
        typer.echo(f"feedback:    {_value_word(record.get('feedback_value'))}")
        typer.echo(f"source:      {record.get('source_product') or '—'}")
        typer.echo(f"channel:     {record.get('channel') or '—'}")

        tags = record.get("tags") or []
        if tags:
            typer.echo(f"tags:        {', '.join(str(tag) for tag in tags)}")

        target_type = record.get("target_type")
        if target_type:
            typer.echo(f"target:      {target_type}")
        target_text = record.get("target_text")
        if target_text:
            typer.echo(f"target_text: {target_text}")

        event_at = record.get("event_at")
        if event_at:
            typer.echo(f"event_at:    {event_at}")
        typer.echo(f"ingested_at: {record.get('ingested_at')}")

        user_comment = record.get("comment")
        if user_comment:
            typer.echo(f"user note:   {user_comment}")

        typer.echo("")
        typer.echo("message:")
        typer.echo(record.get("message") or "—")

        comments = record.get("comments") or []
        if comments:
            typer.echo("")
            typer.echo("operator comments:")
            for comment in comments:
                author = comment.get("author") or "—"
                typer.echo(f"  [{author}] {comment.get('body') or ''}")

        attachments = record.get("attachments") or []
        if attachments:
            typer.echo("")
            typer.echo("attachments:")
            for attachment in attachments:
                filename = attachment.get("filename") or "—"
                typer.echo(f"  {filename}  {attachment.get('url')}")


def register(app: typer.Typer) -> None:
    """Mount the read-only ``feedback`` command group on the root app."""

    feedback_app.command("list")(_feedback_list)
    feedback_app.command("search")(_feedback_search)
    feedback_app.command("show")(_feedback_show)

    app.add_typer(feedback_app, name="feedback")
