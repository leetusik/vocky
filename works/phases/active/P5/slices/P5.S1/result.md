# P5.S1 result — CLI foundation

Built the `vocky` CLI spine: the Typer app skeleton, the packaging rename that makes `vocky` the user CLI and moves the server to `vocky-server`, the on-disk config/credential store, and the shared httpx client + error contract. **No auth/projects/feedback commands** — those are S2–S4; this slice leaves clean `app.add_typer(...)` extension points. Pure client, no backend touched.

## What was built

### New CLI package `src/vocky/cli/`
- **`config_store.py`** — JSON store at `config_dir()/config.json`. `config_dir()` precedence: `VOCKY_CONFIG_DIR` > `$XDG_CONFIG_HOME/vocky` > `~/.config/vocky`. Dir created `0700`, file written `0600` (`os.open(..., 0o600)` + `chmod` to tighten a pre-existing file too). API: `load()`, `save(dict)`, `get_token()/set_token()/clear_token()`, `get_base_url()/set_base_url()`.
- **`client.py`** — `ApiClient(base_url, *, token=None, timeout=30, transport=None)`, a context-manager wrapper over `httpx.Client` (mirrors `smoke.py`, reuses `make_http_user_agent`). `get/post/delete(path, *, auth=True, token=None, json=None, params=None)` inject `Authorization: Bearer <token>`, parse JSON (or `None` on 204/empty). Typed errors: `CliError(message)` and `ApiError(status_code, detail)` (subclass). Mapping — any `401` → `CliError("Not signed in — run \`vocky login\`.")`; other non-2xx → `ApiError` surfacing `{"detail": ...}` (falls back to text / `HTTP <code>`); transport failure → `CliError("Could not reach vocky at <base_url> ...")`.
- **`app.py`** — root `typer.Typer(no_args_is_help=True, add_completion=False)`. `@app.callback(invoke_without_command=True)` handles eager `--version` (`importlib.metadata.version("vocky")` → `0.1.0`) and global `--base-url`, and stashes a `CliContext` (resolved `base_url`, `store`, `make_client(...)`) on `ctx.obj`. `resolve_base_url()` implements precedence flag > `VOCKY_BASE_URL` > stored > `http://127.0.0.1:8000`. Shared `fail(msg)` + `cli_errors()` context manager so S2–S4 render `CliError` to stderr and exit 1 without boilerplate. `main()` is the console-script target.
- **`__init__.py`** — re-exports `app`, `main`.

### Packaging / rename (exactly 4 files + dependency)
- `pyproject.toml` `[project.scripts]`: `vocky = "vocky.cli:main"` (new CLI) and `vocky-server = "vocky.main:main"` (renamed server); `vocky-smoke`/`vocky-worker` unchanged. `typer>=0.27.0` added to dependencies via `uv add typer` (also updated `uv.lock`).
- `Dockerfile:18` CMD `vocky` → `vocky-server`.
- `docker-compose.yml:51` app `command` `vocky` → `vocky-server` (worker left as `vocky-worker`).
- `README.md:103` "Running The App Directly": `uv run vocky` → `uv run vocky-server`.
- Makefile untouched (it starts the server through Compose, not a direct `uv run vocky`), per the plan.

### Test
- `tests/test_cli_foundation.py` — 5 terse cases, no server/DB: config-store round-trip + `0600` file / `0700` dir perms + `VOCKY_CONFIG_DIR` override (via `tmp_path`+`monkeypatch`, never real `~`); base-URL precedence (flag > env > stored > default); client Bearer injection + JSON parse; `401` → login-hint `CliError` (not `ApiError`); `400 {"detail":...}` → `ApiError` surfacing the detail. Error-mapping cases use `httpx.MockTransport`.

## Verification (all passing)

| Command | Result |
|---------|--------|
| `uv add typer` + `uv sync` | typer 0.27.0 added as direct dep; sync clean (61 packages audited) |
| `uv run python -c "import vocky.cli"` | `ok` — imports clean |
| `uv run vocky --version` | `0.1.0` |
| `uv run vocky --help` | root help renders (shows `--base-url`, `--version`, `--help`) |
| bare `uv run vocky` | prints help, no traceback (exit 2 — Typer's `no_args_is_help` code) |
| entry points | `{'vocky': 'vocky.cli:main', 'vocky-server': 'vocky.main:main', 'vocky-smoke': ..., 'vocky-worker': ...}` — swap confirmed |
| `uv run pytest tests/test_cli_foundation.py` | `5 passed in 0.05s` |
| `python3 scripts/workflow.py validate` | `Workflow validation passed.` |

## Doc impact (recorded in `phase.md`, not versioned here)
Appended one note: console-script rename `vocky` → `vocky-server` + new `vocky` CLI (`~/.config/vocky/` session store, `VOCKY_CONFIG_DIR` override, `typer` direct dep) — for REVIEW to consolidate into `operations.md` / `experience.md`. Did **not** run `doc-new-version`.

## Deviations from plan
None. `src/vocky/admin_assets/docs.json` and all server endpoints/models left untouched; no commit and no status transition performed.
