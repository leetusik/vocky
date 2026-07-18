# P5.S3 — Projects, credentials & usage commands (`/app/*`)

## Context

Third slice of **P5**. With auth (S2) in place, add the control-plane commands a signed-in user needs to actually set up vocky: manage **projects**, mint/list/revoke per-project **`vk_` keys** (the show-once credential their product backend uses), and see **usage**. All session-authed over `/app/*`. Pure client — no backend change.

Read `works/phases/active/P5/phase.md` first (Findings, Constraints, S1/S2 cross-slice notes). Follow the S2 module pattern exactly (see `src/vocky/cli/auth.py`): a command module exposing `register(app)`, importing only from `context`/`config_store`/`client`. Reuse `CliContext.make_client()`, `config_store`, `ApiClient`, `cli_errors`, `fail`.

Backend contract (from `phase.md` Findings): `GET /app/projects` → `{projects:[{id,name,tenant_id,created_at}]}`; `POST /app/projects {name}` → `201 {project}` (400 bad name); `GET /app/projects/{id}` → `{project}` (400 malformed uuid, 404 not found/cross-tenant); `POST /app/projects/{id}/credentials {name?}` → `201 {credential, key:"vk_…"}` **key shown once**; `GET /app/projects/{id}/credentials` → `{credentials:[{id,name,token_prefix,created_at,last_used_at,revoked_at}]}`; `DELETE /app/projects/{id}/credentials/{cid}` → `204`; `GET /app/usage` → `{window,totals,daily_counts,projects}`; `GET /app/projects/{id}/usage` → `{window,totals,daily_counts,credentials}`.

## Approach

**1. Add a shared "must be signed in" seam** to `CliContext` (`src/vocky/cli/context.py`):
```python
def authed_client(self) -> ApiClient:
    if config_store.get_token() is None:
        fail("Not signed in — run `vocky login`.")
    return self.make_client()
```
So every session command gets the friendly "run `vocky login`" up front when no token is stored (a no-token request would otherwise 401 into a raw `ApiError`, not the hint). S3/S4 use `context.authed_client()`; leave S2's `whoami`/`logout` as they are.

**2. New `src/vocky/cli/projects.py`** — two `typer.Typer()` sub-apps + one top-level command, all in this module, wired by `register(app)`:
- `app.add_typer(projects_app, name="projects")`, `app.add_typer(keys_app, name="keys")`, `app.command("usage")(_usage)`.

**`vocky projects` group** (each wraps its body in `with cli_errors():`, uses `ctx.obj.authed_client()`):
- `list` → `GET /app/projects`; print each project's short id + name + created date; empty → `No projects yet. Create one with \`vocky projects create <name>\`.`
- `create <name>` (argument) → `POST /app/projects {name}`; print `Created project "<name>" (<id>).` 400 detail surfaces (e.g. blank/too-long name).
- `show <project_id>` (argument) → `GET /app/projects/{id}`; print id, name, created_at. 404/400 detail surfaces.

**`vocky keys` group** (keys belong to a project → `--project <id>` required option on each):
- `mint --project <id> [--name <label>]` → `POST /app/projects/{id}/credentials {name?}`; print the show-once panel: a warning line — `Copy this key now — it is shown only once and cannot be recovered. If you lose it, revoke it and mint a new one.` — then the `key` value (`vk_…`) on its own line. This is the key UX contract (mirrors the web show-once copy).
- `list --project <id>` → `GET /app/projects/{id}/credentials`; print each credential's `token_prefix`, name, created, `last_used_at` (or "never"), and revoked state; empty → `No keys yet. Mint one with \`vocky keys mint --project <id>\`.`
- `revoke --project <id> <credential_id>` (argument) → `DELETE /app/projects/{id}/credentials/{cid}`; print `Revoked key <credential_id>.` 404 detail surfaces.

**`vocky usage` command** — `--project <id>` optional; `--start` / `--end` optional ISO-8601 passthrough:
- no `--project` → `GET /app/usage`; print the window + totals (total / liked / disliked / unrated) and the project list.
- with `--project` → `GET /app/projects/{id}/usage`; print the window + totals and each credential's `token_prefix` + `last_used_at`.

Keep output plain and readable (`typer.echo`, light alignment) — no new deps and no `rich` tables needed; plain text stays easy to test and read.

**3. `src/vocky/cli/app.py`** — at the bottom, add `from vocky.cli import projects` and `projects.register(app)` alongside the existing `auth.register(app)`.

## Files
- `src/vocky/cli/context.py` — add `CliContext.authed_client()`.
- `src/vocky/cli/projects.py` — **new**; `projects` + `keys` groups, `usage` command, `register`.
- `src/vocky/cli/app.py` — register `projects`.
- `tests/test_cli_projects.py` — **new**, small.

## Tests (keep small — one terse file)

`tests/test_cli_projects.py`: `CliRunner` + `httpx.MockTransport` + `VOCKY_CONFIG_DIR`→`tmp_path` with a token pre-stored (so `authed_client` passes); inject the transport by monkeypatching the client factory. ~5 cases:
- `projects create foo` → prints created id/name (POST 201).
- `projects list` empty → the "No projects yet" hint (GET 200 `{projects:[]}`).
- `keys mint --project <id>` → prints the `vk_…` key **and** the show-once warning line (POST 201).
- `keys revoke --project <id> <cid>` → "Revoked …" (DELETE 204).
- any command with **no** stored token → "run `vocky login`", exit 1, no HTTP call.

## Verification (run the code end-to-end)

The local server is up at `http://127.0.0.1:8000` (S2 ran against it). Using a throwaway `VOCKY_CONFIG_DIR` and a fresh signed-up account:
- `uv run vocky projects create "cli demo"` → prints id; `uv run vocky projects list` shows it.
- `uv run vocky keys mint --project <id> --name backend` → prints the show-once warning + a `vk_…` key; `uv run vocky keys list --project <id>` shows the `token_prefix` (never the full key).
- `uv run vocky usage` → tenant totals + project list; `uv run vocky usage --project <id>` → project totals + credentials.
- `uv run vocky keys revoke --project <id> <credential_id>` → "Revoked …".
- `uv run pytest tests/test_cli_projects.py tests/test_cli_auth.py tests/test_cli_foundation.py` all green.
- `python3 scripts/workflow.py validate` passes.

## Notes for the executor
- Pure client — no server/`admin_assets` changes.
- Append a one-line **"Doc impact"** note to `phase.md` (the `projects`/`keys`/`usage` command surface + the CLI show-once key crossing) for REVIEW to fold into `experience.md`. Do **not** run `doc-new-version`.
- Write `result.md`; append cross-slice notes (the `authed_client()` seam + `add_typer` group pattern) so S4's `feedback` group follows suit. Do not commit or transition status.
