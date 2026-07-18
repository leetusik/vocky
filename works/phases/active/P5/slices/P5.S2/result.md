# P5.S2 result — Auth commands: `signup` / `login` / `logout` / `whoami`

## What I built

Four **top-level** auth commands on the `vocky` CLI driving the public `/auth/*`
surface and the on-disk session token — the headless onboarding entry point.
Pure client: no server endpoint, middleware, model, or `admin_assets/docs.json`
touched.

### Files changed

- **`src/vocky/cli/client.py`** — made the `401` mapping **token-aware**.
  `_handle` now takes `token_sent: bool` (threaded from `request()` via
  `bool(effective_token)`): a `401` on a request that *sent* a token → the
  existing `CliError("Not signed in — run \`vocky login\`.")` (session expired);
  a `401` on an *unauthenticated* request (no token) → `ApiError(401, detail)`
  so login/signup can render their own copy. Module docstring updated.
- **`src/vocky/cli/context.py`** — **new**. Extracted the shared helpers
  (`CliContext`, `resolve_base_url`, `fail`, `cli_errors`, `DEFAULT_BASE_URL`)
  out of `app.py`. Imports only `config_store` + `client` (nothing from `app` or
  a command module), so command modules can reuse them with no import cycle.
- **`src/vocky/cli/app.py`** — now imports those helpers from `context` and
  **re-exports** `DEFAULT_BASE_URL` + `resolve_base_url` (plus `CliContext`,
  `fail`, `cli_errors`) via `__all__`, so `from vocky.cli.app import
  DEFAULT_BASE_URL, resolve_base_url` (S1 test) keeps working unchanged. Keeps
  `app`, the `--version` / `--base-url` callback, and `main()`. Registers command
  modules at the bottom: `from vocky.cli import auth; auth.register(app)`.
- **`src/vocky/cli/auth.py`** — **new**. `_signup` / `_login` / `_logout` /
  `_whoami` plus `register(app)`. Shared `_read_credentials` reads `--email` (or
  an interactive prompt) and the password from a hidden confirm prompt or a
  single line of stdin via `--password-stdin` (agent path — password never on
  argv).
- **`tests/test_cli_auth.py`** — **new**, 4 terse cases (CliRunner +
  `httpx.MockTransport` + `VOCKY_CONFIG_DIR`→`tmp_path`).

### Command behaviour (as specified in the plan)

- **`vocky signup`** — `make_client(use_stored_token=False).post("/auth/signup",
  …, auth=False)`. `201` → `set_token`, prints `Signed up and signed in as
  <email>.` + `A workspace "<tenant.name>" was created for you automatically.`
  `409` → `An account with that email already exists — run \`vocky login\`.`
  `400` (e.g. password < 8) → server `detail` surfaced via `cli_errors`.
- **`vocky login`** — `post("/auth/login", …, auth=False)`. `200` → store token,
  `Signed in as <email>.` `401` (now an `ApiError`, unauthenticated) → generic
  `Incorrect email or password.` — no enumeration, no token stored.
- **`vocky logout`** — best-effort `post("/auth/logout")` with the stored token
  (any error ignored — idempotent/`204`), then `clear_token()`, `Signed out.`
  Friendly even when no token was stored (no HTTP call in that case).
- **`vocky whoami`** — no stored token → `Not signed in — run \`vocky login\`.`
  with no HTTP call; else `get("/auth/me")` → `Signed in as <email>.` +
  `Workspace(s): …`. A `401` here (token sent, expired) flows through the
  client's session-expired hint.

## Key decisions

- **`context.py` over keeping helpers in `app.py`.** The plan's registration
  pattern (`auth.register(app)` from the bottom of `app.py`) needs command
  modules to import `CliContext`/`cli_errors`/`fail` without importing `app`
  (which imports them). Extracting to a helper module that depends only on
  `config_store`/`client` breaks the cycle cleanly and gives S3/S4 the same
  seam. `app.py` re-exports the two names the S1 test imports.
- **Errors → stderr, success → stdout.** `fail`/`cli_errors` already write to
  stderr; commands print success to stdout. (click 8.3's CliRunner separates the
  two, so the tests assert on `result.stderr` vs `result.stdout`.)
- **`--password-stdin` reads exactly one line** (`sys.stdin.readline().rstrip(
  "\r\n")`) and errors if empty, so agents pipe the password instead of exposing
  it on argv.

## Verification

Ran **all** of the plan's verification, including the live end-to-end flow — a
local server was reachable at `http://127.0.0.1:8000` (docker stack already up),
so I did **not** need `make bootstrap`. Every live command used a throwaway
`VOCKY_CONFIG_DIR` (a `mktemp -d`) so the operator's real `~/.config/vocky` was
never touched.

**Live end-to-end (real server), fresh `cli-<ts>@example.com`:**

```
== signup ==
Signed up and signed in as cli-1784336522@example.com.
A workspace "cli-1784336522's workspace" was created for you automatically.
-- config file perms --   600 .../vocky/config.json
== whoami ==
Signed in as cli-1784336522@example.com.
Workspace: cli-1784336522's workspace
== login wrong password (expect exit 1) ==
Incorrect email or password.
exit=1
== logout ==
Signed out.
== whoami after logout (expect login hint, exit 1) ==
Not signed in — run `vocky login`.
exit=1
```

The config file was written `0600`; token stored on signup, cleared on logout.

**Unit tests:**

```
uv run pytest tests/test_cli_auth.py tests/test_cli_foundation.py -q
9 passed in 0.07s
```

Both files green — the S1 token-aware 401 test (`test_client_401_maps_to_login_hint`,
sends `token="stale"`) still gets the login hint. Broader `-k cli` run: 9 passed,
169 deselected.

**Workflow state integrity:**

```
python3 scripts/workflow.py validate
Workflow validation passed.
```

## Deviations from plan

None. Scope held to the four auth commands; projects/keys/usage (S3) and
feedback (S4) left untouched, with the `register(app)` seam clean for them.

## Doc impact

Appended a one-line **Doc impact** note to `phase.md` (the four-command
`vocky signup/login/logout/whoami` surface + `--password-stdin` agent path, for
REVIEW to fold into `experience.md`). Did **not** run `doc-new-version`.

Cross-slice notes appended to `phase.md`: the `register(app)` + `context.py`
pattern (with grouped-sub-app guidance for S3/S4) and the token-aware 401
contract.
