"""``vocky capture`` — post feedback to ``/api/feedback`` with a ``vk_`` key.

This is the CLI's first command on the ``vk_``-keyed side of the auth split
(see :mod:`vocky.cli.projects`'s module docstring for the invariant): every
other command authenticates with the stored **session** token; ``capture``
authenticates with the ``vk_`` **ingest** key resolved from the
``VOCKY_API_TOKEN`` environment variable, and never with the session token.

Follows the command-module shape (see :mod:`vocky.cli.projects`): define the
body here and expose a :func:`register` that mounts it on the root app —
importing only from ``context`` / ``client`` (never ``app``) so registration
from the bottom of :mod:`vocky.cli.app` cannot form an import cycle.

Import isolation is load-bearing here: this module (and every module under
``vocky.cli``) may import only typer / httpx / stdlib / the httpx-only
``vocky.smoke`` — never :mod:`vocky.capture`, whose schema pulls in pydantic
and would silently break the lean (httpx + typer only) install. The request
body is therefore hand-built as a plain ``dict``, not built from that module's
models.
"""

from __future__ import annotations

import sys
from typing import Any

import typer

from vocky.cli.context import CliContext, cli_errors, resolve_api_token

_UNAUTHORIZED_MESSAGE = (
    "Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked)."
)


def _resolve_message(message: str) -> str:
    """Return ``message`` as given, or the full contents of stdin when it is ``-``."""

    if message == "-":
        return sys.stdin.read().rstrip("\n")
    return message


def _build_payload(
    *,
    message: str,
    product: str,
    integration: str | None,
    value: int | None,
    comment: str | None,
    tags: list[str],
    session_id: str | None,
    user_id: str | None,
    project: str | None,
) -> dict[str, Any]:
    """Hand-build the ``/api/feedback`` request body, omitting unset keys.

    ``source`` is the only nested object (mirroring ``src/vocky/smoke.py``'s
    in-tree reference payload); every other supplied field is a top-level key.
    A key is omitted entirely rather than sent as an explicit ``null`` when the
    user did not supply it.
    """

    payload: dict[str, Any] = {"message": message, "source": {"product": product}}
    if integration:
        payload["source"]["integration"] = integration
    if value is not None:
        payload["feedback_value"] = value
    if comment is not None:
        payload["comment"] = comment
    if tags:
        payload["tags"] = tags
    if session_id is not None:
        payload["session_id"] = session_id
    if user_id is not None:
        payload["user_id"] = user_id
    if project is not None:
        payload["project"] = project
    return payload


def _capture(
    ctx: typer.Context,
    message: str = typer.Argument(
        ...,
        metavar="MESSAGE",
        help="The feedback message. Pass `-` to read it from stdin.",
    ),
    product: str = typer.Option(
        ...,
        "--product",
        metavar="PRODUCT",
        help="Source product name (required, non-blank). Maps to `source.product`.",
    ),
    integration: str | None = typer.Option(
        None,
        "--integration",
        metavar="INTEGRATION",
        help="Source integration name. Maps to `source.integration`.",
    ),
    value: int | None = typer.Option(
        None,
        "--value",
        metavar="N",
        help="1 = liked, 2 = disliked.",
    ),
    comment: str | None = typer.Option(
        None,
        "--comment",
        metavar="TEXT",
        help="An optional user comment.",
    ),
    tag: list[str] = typer.Option(
        [],
        "--tag",
        metavar="TAG",
        help="A tag to attach. Repeatable.",
    ),
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        metavar="SESSION_ID",
        help="Groups this capture with others from the same conversation.",
    ),
    user_id: str | None = typer.Option(
        None,
        "--user-id",
        metavar="USER_ID",
        help="The end user's id.",
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        metavar="PROJECT",
        help=(
            "Destination project name. Honored only for an org-level `vk_` key "
            "— a project-bound key ignores it."
        ),
    ),
) -> None:
    """Capture feedback to `POST /api/feedback` with a `vk_` ingest key.

    Authenticates with the `vk_` key read from the `VOCKY_API_TOKEN`
    environment variable — never with the stored session token every other
    `vocky` command uses.
    """

    with cli_errors():
        context: CliContext = ctx.obj
        api_token = resolve_api_token()
        message_value = _resolve_message(message)
        payload = _build_payload(
            message=message_value,
            product=product,
            integration=integration,
            value=value,
            comment=comment,
            tags=tag,
            session_id=session_id,
            user_id=user_id,
            project=project,
        )

        with context.make_client(token=api_token, use_stored_token=False) as client:
            result = client.post(
                "/api/feedback",
                json=payload,
                unauthorized_message=_UNAUTHORIZED_MESSAGE,
            )

        typer.echo(f"Captured — request_id {result['request_id']}")


def register(app: typer.Typer) -> None:
    """Mount the top-level `capture` command on the root app."""

    app.command("capture")(_capture)
