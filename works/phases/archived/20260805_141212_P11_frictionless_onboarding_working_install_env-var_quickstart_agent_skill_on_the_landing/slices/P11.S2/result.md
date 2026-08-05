# P11.S2 — Result

## What landed

- **`resolve_api_token()`** — module-level function in `src/vocky/cli/context.py`, right beside
  `resolve_base_url`. Precedence is one tier: `VOCKY_API_TOKEN` (stripped, empty/whitespace treated as
  absent) or fail. No `--token` flag, no config-store persistence. Failure message (exact string):
  ```
  VOCKY_API_TOKEN is not set — mint a key with `vocky keys mint` and export it.
  ```
- **`src/vocky/cli/capture.py`** (new) — a top-level `vocky capture MESSAGE --product PRODUCT [options]`
  command. `MESSAGE` is a positional `typer.Argument`; passing exactly `-` reads the whole message from
  stdin (`sys.stdin.read().rstrip("\n")`). Options: `--product` (required, `str`), `--integration`,
  `--value` (`int`, help `1 = liked, 2 = disliked.`), `--comment`, `--tag` (repeatable, omitted from the
  body when empty), `--session-id`, `--user-id`, `--project` (help names the org-only honoring). The body is
  hand-built (`_build_payload`) — no import from `vocky.capture`, no pydantic. Uses
  `context.make_client(token=api_token, use_stored_token=False)` exactly as specified, then
  `client.post("/api/feedback", json=payload, unauthorized_message=_UNAUTHORIZED_MESSAGE)`. Success output
  (exact string, `request_id` printed in full):
  ```
  Captured — request_id <full id>
  ```
- **The 401 trap fix** — `ApiClient.request` and `ApiClient._handle` (`src/vocky/cli/client.py`) both gained
  a keyword-only `unauthorized_message: str | None = None` parameter threaded from `request` → `_handle`.
  When set it replaces the default `"Not signed in — run \`vocky login\`."` on a token-bearing 401. Every
  existing caller (`auth.py`, `projects.py`, `feedback.py`) omits the parameter, so the default preserves
  today's behavior verbatim — confirmed by the unchanged 26/26 pass on the four pre-existing CLI test
  files. `capture.py`'s override (exact string):
  ```
  Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).
  ```
- **`_keys_mint` hint line** (`src/vocky/cli/projects.py`) — one new `typer.echo` inserted **before** the
  final plaintext-key line (never after — the key stays last):
  ```
  Export it for `vocky capture` and agent skills:  export VOCKY_API_TOKEN=<the key below>
  ```
  No existing `tests/test_cli_projects.py` assertion needed adjusting: both mint tests assert only
  `"shown only once" in result.stdout` and that the **last** stdout line is the plaintext key — the new
  hint line sits between those two and doesn't collide with either assertion.
- **Registration** (`src/vocky/cli/app.py`) — `from vocky.cli import capture` added to the deferred-import
  block, alphabetically first; `capture.register(app)` called before `projects.register(app)` /
  `feedback.register(app)` (after `auth.register(app)`).
- **Version bump** — `pyproject.toml` `version = "0.1.0"` → `"0.2.0"`. `uv lock` re-run (exit 0, resolved
  64 packages, `uv.lock`'s `vocky` entry now reads `0.2.0`). Confirmed `vocky --version` from the built
  wheel prints `0.2.0` (see validation step 6) — the in-place `uv run vocky --version` would *not* show the
  new number until a reinstall, since `--version` reads `importlib.metadata.version("vocky")` (installed
  metadata), not the source tree; this is expected, not a defect.
- **Docs** (`docs/cli.md`): added a `VOCKY_API_TOKEN` paragraph beside the session-store section; corrected
  the now-false "everything sends the session token" sentence (now carves out `vocky capture`); corrected
  the "Generic-401 semantics" bullet the same way; added a `### Capture` command-reference section with the
  real invocation and export quickstart; and updated the walkthrough's step 4 (previously "Capture is not a
  CLI command in this release", now false) to show both `vocky capture` and the raw-HTTP equivalent — this
  last edit is not explicitly called out in the plan's doc list but was needed to avoid the same file
  contradicting itself two sections apart; it's a direct, minimal correction of newly-false text in the
  same doc the plan already opens for editing, not a scope expansion. Did **not** touch the stale "PyPI
  publishing is P6" lines at `docs/cli.md:11` / `README.md:50` (confirmed still present, reserved for
  `P11.S3`/`P11.S4`).

## Tests

New `tests/test_cli_capture.py`, 3 tests, `CliRunner` + `httpx.MockTransport` via the same
`CliContext.make_client` monkeypatch shape as `tests/test_cli_projects.py`, `config_env` fixture adds
`monkeypatch.delenv("VOCKY_API_TOKEN", raising=False)`:

1. Happy path — `VOCKY_API_TOKEN` set, asserts `POST /api/feedback`, nested `{"source": {"product": …}}`,
   `Authorization: Bearer vk_test…` (not the session token), 202 response, `exit_code == 0`, request id in
   stdout.
2. Missing token — `VOCKY_API_TOKEN` unset, no HTTP call made (handler raises if hit), non-zero exit,
   `VOCKY_API_TOKEN` in stderr.
3. 401 — handler returns 401, non-zero exit, `VOCKY_API_TOKEN` in stderr, `"vocky login"` **not** in
   stderr.

## Validation — verbatim output

**1. `uv run pytest tests/test_cli_capture.py -q`**
```
3 passed in 0.09s
```

**2. `uv run pytest tests/test_cli_foundation.py tests/test_cli_auth.py tests/test_cli_projects.py tests/test_cli_feedback.py -q`**
```
26 passed in 0.15s
```
Confirms the `unauthorized_message` default changed nothing for the four pre-existing CLI test files.

**3. `uv run pytest -q` — full-suite baseline comparison**

This environment has a live Postgres reachable at the test suite's default `127.0.0.1:55432` (confirmed
with `nc -z 127.0.0.1 55432` → open), unlike the "no Postgres running" environment the plan's ~108-error
baseline (documented in `P6.S9`'s result) describes. So instead of pinning to that number, I established a
same-environment pre/post-slice comparison by `git stash`-ing every source/test/doc/lockfile change this
slice made and re-running the full suite, then restoring the stash:

- **Pre-slice** (stashed): `206 passed in 9.19s` — 0 errors.
- **Post-slice**: `209 passed in 9.17s` — 0 errors.

209 − 206 = 3, exactly the 3 new `test_cli_capture.py` tests. **No pre-existing failures/errors grew** —
in this environment there were zero to begin with, and there are zero after. (If a later run of this same
validation is done in an environment with no Postgres running, expect the suite to show the ~108
pre-existing `psycopg.OperationalError`s again, unrelated to this slice's changes — the CLI's own tests
never touch a database.)

**4. `uv run vocky capture --help` / `uv run vocky --help`**

Both render. `capture --help` shows the docstring, the `MESSAGE` argument, and all 8 options with
`metavar=`/period-ending help. `vocky --help`'s command list includes:
```
signup    Create an account (and its auto-provisioned org) and sign in.
login     Sign in to an existing account and store the session token.
logout    Sign out: best-effort server revoke, then drop the local token.
whoami    Show the signed-in account and its org(s).
capture   Capture feedback to `POST /api/feedback` with a `vk_` ingest key.
usage     Show capture usage for your org or a single project.
projects  Manage the projects under your org.
keys      Mint, list, and revoke a project's `vk_` ingest keys.
feedback  Read and search feedback across your org's projects.
```

**5. `uv lock`**
```
Resolved 64 packages in 3ms
```
Exit 0.

**6. `uv build && uvx --no-cache --from dist/vocky-0.2.0-py3-none-any.whl vocky --version`**
```
Building source distribution...
Building wheel from source distribution...
Successfully built dist/vocky-0.2.0.tar.gz
Successfully built dist/vocky-0.2.0-py3-none-any.whl
Downloading pygments (1.2MiB)
 Downloading pygments
Installed 15 packages in 13ms
0.2.0
```
Prints `0.2.0`. Confirmed the installed set is exactly 15 packages and none of `sqlalchemy` / `uvicorn` /
`psycopg` appear (checked with an isolated `uv run --isolated --no-project --with dist/vocky-0.2.0-py3-none-any.whl python -c "..."` listing `importlib.metadata.distributions()`):
```
['Pygments', 'annotated-doc', 'anyio', 'certifi', 'h11', 'httpcore', 'httpx', 'idna', 'markdown-it-py', 'mdurl', 'rich', 'shellingham', 'typer', 'typing_extensions', 'vocky']
```
The lean-install guard holds.

**7. `grep -rn "^from vocky\.\|^import vocky\." src/vocky/cli/`**
```
src/vocky/cli/auth.py:21:from vocky.cli import config_store
src/vocky/cli/auth.py:22:from vocky.cli.client import ApiError
src/vocky/cli/auth.py:23:from vocky.cli.context import CliContext, cli_errors, fail
src/vocky/cli/client.py:27:from vocky.smoke import make_http_user_agent
src/vocky/cli/feedback.py:23:from vocky.cli.client import ApiError
src/vocky/cli/feedback.py:24:from vocky.cli.context import CliContext, cli_errors, fail
src/vocky/cli/__init__.py:7:from vocky.cli.app import app, main
src/vocky/cli/context.py:19:from vocky.cli import config_store
src/vocky/cli/context.py:20:from vocky.cli.client import ApiClient, CliError
src/vocky/cli/capture.py:29:from vocky.cli.context import CliContext, cli_errors, resolve_api_token
src/vocky/cli/projects.py:22:from vocky.cli.client import ApiError
src/vocky/cli/projects.py:23:from vocky.cli.context import CliContext, cli_errors, fail
src/vocky/cli/app.py:22:from vocky.cli.context import (
src/vocky/cli/app.py:88:from vocky.cli import auth  # noqa: E402  (import after ``app`` exists)
src/vocky/cli/app.py:89:from vocky.cli import capture  # noqa: E402  (import after ``app`` exists)
src/vocky/cli/app.py:90:from vocky.cli import feedback  # noqa: E402  (import after ``app`` exists)
src/vocky/cli/app.py:91:from vocky.cli import projects  # noqa: E402  (import after ``app`` exists)
```
Only `vocky.cli.*` and `vocky.smoke` appear. Import isolation holds.

## What was NOT behaviorally proven

`capture` has **not** been exercised against a real running vocky API — every test stubs the transport
with `httpx.MockTransport`, and validation step 6 only proves the lean-install package graph and
`--version`, not a live `/api/feedback` round trip. The end-to-end proof (a real server, a real `vk_` key,
a real 202 + queryable record) lands in **P12's live smoke**, per the phase's hand-off section.

## Deviations from `plan.md`

- **Full-suite baseline methodology** — the plan expected ~108 pre-existing `psycopg.OperationalError`s
  with no Postgres running; this environment has a live Postgres on the suite's default port, so that
  count doesn't materialize. Established an equivalent pre/post-slice comparison instead (see validation
  step 3) rather than treating the mismatched literal number as a failure. This is a validation-methodology
  adaptation, not a scope or design deviation — the underlying guarantee (no growth in pre-existing
  failures) is upheld either way.
- **One extra docs correction beyond the plan's three bullet points** — `docs/cli.md`'s walkthrough step 4
  ("Capture is not a CLI command in this release") was left false by the plan's three specified edits, so
  it was corrected too (see "Docs" above). No other unplanned edits were made.

Nothing else departed from the plan: the design decisions in `plan.md` §§1–7 (token resolution, client
seam, the 401 override, command shape, registration, the `keys mint` hint, the version bump) were
implemented as specified, not re-litigated.

## Doc impact

Recorded in `phase.md`'s `## Doc impact` section (not versioned here — durable docs are versioned once per
phase, at `P11.REVIEW`).
