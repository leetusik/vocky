# P5.S3 result — Projects, credentials & usage commands

## What was built

A pure-client `/app/*` control-plane command surface for the `vocky` CLI, following the S2 command-module pattern exactly. No backend/`admin_assets` change.

- **`src/vocky/cli/context.py`** — added `CliContext.authed_client()`: the shared "must be signed in" seam. Fails up front with `Not signed in — run \`vocky login\`.` when no session token is stored, else returns `make_client()` (stored-token injection). Every `/app/*` command uses it, so a token-less call gets the friendly hint instead of 401ing into a raw `ApiError`. S2's `whoami`/`logout` left as-is.
- **`src/vocky/cli/projects.py`** (new) — two `typer.Typer()` sub-apps + one top-level command + `register(app)`:
  - `vocky projects list|create|show` over `GET/POST /app/projects`, `GET /app/projects/{id}`. `list` prints short-id + name + created date, empty → `No projects yet. Create one with \`vocky projects create <name>\`.`; `create <name>` → `Created project "<name>" (<id>).`; `show <id>` → id/name/created_at.
  - `vocky keys mint|list|revoke`, each with a required `--project <id>`. `mint --name?` → `POST .../credentials`, prints the **show-once** warning line then the `vk_…` key on its own line (the key UX contract). `list` prints `token_prefix…` + label + created + last-used(or "never") + active/revoked state, never the full key; empty → `No keys yet. Mint one with \`vocky keys mint --project <id>\`.`. `revoke <cid>` → `DELETE` (204) → `Revoked key <cid>.`.
  - `vocky usage [--project <id>] [--start] [--end]` → `GET /app/usage` (tenant totals + project list) or `GET /app/projects/{id}/usage` (project totals + credentials). `--start`/`--end` pass through as `start_ingested_at`/`end_ingested_at` query params (the server's window param names). Plain `typer.echo` output — no new deps, no `rich`.
- **`src/vocky/cli/app.py`** — bottom-of-file `from vocky.cli import projects` + `projects.register(app)` alongside `auth`.
- **`tests/test_cli_projects.py`** (new, 5 cases) — `CliRunner` + `httpx.MockTransport` + `VOCKY_CONFIG_DIR`→`tmp_path` with a token pre-stored; same recipe as `test_cli_auth.py`.

## Key decisions

- `authed_client()` lives on `CliContext` (not per-command) so S4's feedback group reuses the exact same seam — one place enforces "signed in".
- Sub-command groups use `typer.Typer(no_args_is_help=True)` sub-apps mounted via `app.add_typer(...)` inside `register`; `register` binds the leaf commands. This is the clean group pattern S4 should copy for its `feedback` group.
- `keys mint` sends `json=body or None` so an omitted `--name` posts an empty body (the server's `_parse_optional_body` yields defaults) rather than `{"name": null}`.
- Usage window param mapping (`--start`→`start_ingested_at`, `--end`→`end_ingested_at`) chosen to match `usage_api._resolve_usage_window`; verified live.
- Success → stdout, errors → stderr (via `cli_errors`/`fail`), matching S2.

## Verification

**Unit tests** — `uv run pytest tests/test_cli_projects.py tests/test_cli_auth.py tests/test_cli_foundation.py`:
```
14 passed in 0.08s
```

**Workflow validate** — `python3 scripts/workflow.py validate`:
```
Workflow validation passed.
```

**Live end-to-end** (ran — server up at `http://127.0.0.1:8000`, throwaway `VOCKY_CONFIG_DIR` + fresh signed-up account `cli-s3-…@example.com`):
- `projects create "cli demo"` → `Created project "cli demo" (39219ece-…).`
- `projects list` → `39219ece  cli demo  (created 2026-07-18)`
- `projects show <id>` → id / name / `created_at`
- `keys mint --project <id> --name backend` → the show-once warning line + `vk_O_KqcwMEFgG…` (full key printed once)
- `keys list --project <id>` → `3d9f802f-…  vk_O_KqcwMEF…  backend  (created 2026-07-18, last used never, active)` — only the prefix, never the full key
- `usage` → tenant window + `Captured: 0 total (…)` + `Projects:` list
- `usage --project <id>` → project window + totals + `Keys:` with `token_prefix…  last used never`
- `keys revoke --project <id> <cid>` → `Revoked key 3d9f802f-….`; subsequent `keys list` shows the credential as `revoked`

The `vk_` key is shown exactly once on mint and never again (list/usage show only `token_prefix`) — the show-once contract holds against the real server.

## Deviations

None. Followed the plan as written.

## Doc impact (appended to phase.md, not versioned here)

The `projects` / `keys` / `usage` command surface + the CLI show-once `vk_` key crossing — recorded under phase.md "Doc impact" for REVIEW to fold into `experience.md`. Did not run `doc-new-version`.
