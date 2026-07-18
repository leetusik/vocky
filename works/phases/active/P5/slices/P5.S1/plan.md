# P5.S1 — CLI foundation: Typer app, `vocky` script + server→`vocky-server` rename, config store, httpx client

## Context

First slice of **P5: CLI & Agent-First Onboarding**. It builds the **spine** every later CLI command reuses — the Typer app skeleton, the packaging so `vocky` is the user CLI, the on-disk session store, and the shared httpx API client. No commands with real API behavior land here (auth/projects/feedback are S2–S4); S1 makes those slices thin.

Read `works/phases/active/P5/phase.md` first (Findings & Notes, Constraints, Operator decisions) — it's the shared context. **Pure client, no backend change**: the Starlette backend already exposes the whole flow. `src/vocky/smoke.py` (sync `httpx.Client`, Bearer headers, `raise SystemExit` on error) is the pattern to mirror for the client.

Operator-confirmed: **Typer** (promoted to a direct dep), CLI command **`vocky`** with the existing server entry **renamed to `vocky-server`**, on-disk token at **`~/.config/vocky/`** (`0600`). All via `uv` (`uv add`, `uv run`, `uv sync` — no `pip`/`venv`/bare `python`).

## Files to change

**Packaging / rename (the ops-blast-radius bit — exactly 4 files):**
- `pyproject.toml:36-39` `[project.scripts]`: change `vocky = "vocky.main:main"` → `vocky-server = "vocky.main:main"`, and **add** `vocky = "vocky.cli:main"`. Keep `vocky-smoke`, `vocky-worker`. Also add `typer` to `[project.dependencies]` — do it with `uv add typer` (updates `pyproject.toml` + `uv.lock`), not a hand-edit.
- `Dockerfile:18` `CMD [..., "vocky"]` → `"vocky-server"`.
- `docker-compose.yml:51` app service `command: [..., "vocky"]` → `"vocky-server"` (worker already `vocky-worker` — leave it).
- `README.md:103` `uv run vocky` (under "Running The App Directly") → `uv run vocky-server`. This is the only mechanical README touch S1 makes; the full content refresh is S5.

(The Makefile needs **no** change — it starts the server through Compose, not a direct `uv run vocky`. Other `"vocky"` grep hits are the health-JSON `{"service":"vocky"}` string and the brand wordmark — not the console entry.)

**New CLI package `src/vocky/cli/`:**
- `__init__.py` — re-export `app` and `main`.
- `app.py` — root `typer.Typer(no_args_is_help=True, help=...)`. A `@app.callback(invoke_without_command=True)` handling a global `--base-url` option and an eager `--version` flag (`importlib.metadata.version("vocky")` → prints `0.1.0`, then `raise typer.Exit()`). Resolve the base URL once here and stash a small context object on `ctx.obj` (resolved base URL + the config store) for sub-commands. `def main() -> None: app()` is the console-script target. No feedback/auth/project commands yet — S2–S4 attach their sub-apps here via `app.add_typer(...)`.
- `config_store.py` — the on-disk store under `config_dir()`: `VOCKY_CONFIG_DIR` if set, else `$XDG_CONFIG_HOME/vocky` else `~/.config/vocky`. A `config.json` holding `{ "base_url"?: str, "token"?: str }`. API: `load() -> dict`, `save(data)` (creates dir `0700`, writes file `0600` via `os.open(..., 0o600)` / `os.chmod`), plus typed helpers `get_token()`, `set_token(t)`, `clear_token()`, `get_base_url()/set_base_url()`. This is the new home-dir convention (none existed before).
- `client.py` — a thin sync wrapper over `httpx.Client` (mirroring `smoke.py`): holds resolved `base_url` + optional bearer token + `User-Agent` (reuse `VOCKY_HTTP_USER_AGENT`/default). Methods `get/post/delete(path, *, auth=True/token=..., json=..., params=...)` that inject `Authorization: Bearer <token>` when a token is present, parse JSON, and translate outcomes into a typed `ApiError(status, detail)` / `CliError(message)`:
  - any `401` → `CliError("Not signed in — run \`vocky login\`.")`
  - other 4xx/5xx → surface the server's `{"detail": ...}` (falling back to status text)
  - connection failure → a friendly "could not reach vocky at <base_url>" message.
  Commands catch `CliError` and exit non-zero with the message on stderr (`typer.secho(err=True)` + `raise typer.Exit(1)`) — a shared helper so S2–S4 don't each reinvent it.

**Base-URL resolution precedence** (implement once in `app.py`): `--base-url` flag → `VOCKY_BASE_URL` env → config store `base_url` → default `http://127.0.0.1:8000`.

## Tests (keep small — one terse file)

`tests/test_cli_foundation.py`, a handful of high-value cases only:
- config store round-trips `base_url` + `token`; the written file is mode `0600`; `VOCKY_CONFIG_DIR` override is honored (use `tmp_path` + monkeypatch, never the real `~`).
- base-URL resolution precedence (flag > env > stored > default).
- client error mapping: `401` → the "run `vocky login`" `CliError`; a `{"detail":"x"}` `400` surfaces `x`. Use `httpx.MockTransport` so no server is needed.

No fixture sprawl; follow the repo's existing flat `tests/test_*.py` style.

## Verification (end-to-end, run the code)

- `uv add typer` then `uv sync`; `uv run python -c "import vocky.cli"` imports clean.
- `uv run vocky --version` → `0.1.0`; `uv run vocky --help` shows the root help; bare `uv run vocky` prints help (no traceback).
- Confirm the entry-point swap: `vocky` now routes to the CLI (the `--version` above proves it), and the server moved to `vocky-server` (pyproject shows `vocky-server = "vocky.main:main"`; `Dockerfile`/`docker-compose.yml` updated).
- `uv run pytest tests/test_cli_foundation.py` passes.
- `python3 scripts/workflow.py validate` passes (state integrity).

## Notes for the executor

- Append a one-line **"Doc impact"** note to `phase.md` recording the server console-script rename (`vocky` → `vocky-server`; new `vocky` CLI) so the REVIEW slice updates the durable `operations.md`/`experience.md`. Do **not** run `doc-new-version`.
- Do not add auth/projects/feedback commands — that's S2–S4. Leave clear extension points (`app.add_typer`).
- Do not touch `src/vocky/admin_assets/docs.json` (stale, P6 removal) or any server endpoint/model.
- Write `result.md`; do not commit and do not transition status (the orchestrator does both).
