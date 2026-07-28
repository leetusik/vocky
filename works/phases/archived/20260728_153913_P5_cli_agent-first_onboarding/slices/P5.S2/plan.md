# P5.S2 — Auth commands: `signup` / `login` / `logout` / `whoami`

## Context

Second slice of **P5**. On top of the S1 foundation, add the four **top-level** auth commands that drive `/auth/*` and manage the on-disk session token. This is the entry point of the whole onboarding flow ("let's say you are my user" — an agent signs the user up and in headlessly).

Read `works/phases/active/P5/phase.md` first (Findings, Constraints, S1 cross-slice notes). Reuses S1 as-is: `config_store` (`get_token`/`set_token`/`clear_token`), `ApiClient` (`src/vocky/cli/client.py`), and the `ctx.obj` `CliContext.make_client(token=..., use_stored_token=...)` factory in `src/vocky/cli/app.py`. Backend contract: `POST /auth/signup {email,password}` → `201 {token, user:{email}, tenant:{name}}`; `POST /auth/login {email,password}` → `200 {token, user:{email}, tenants:[...]}` (generic `401 invalid email or password`); `POST /auth/logout` (bearer) → `204` idempotent; `GET /auth/me` (bearer) → `{user, tenants}`. **Pure client — no backend change.**

## Approach

**1. Make the client's 401 mapping token-aware** (`src/vocky/cli/client.py`).
Today `_handle` maps *every* 401 to `CliError("Not signed in — run \`vocky login\`.")`, which is wrong for `login`/`signup` (an unauthenticated 401 there means *bad credentials*, not *session expired*). Change `request()` to thread whether a bearer token was actually sent into handling:
- 401 **with** a token sent → `CliError("Not signed in — run \`vocky login\`.")` (session expired).
- 401 **without** a token → `ApiError(401, detail)` (login/signup surface it as "Incorrect email or password").
Keep the existing S1 test green — `tests/test_cli_foundation.py::test_client_401_maps_to_login_hint` sends `token="stale"`, so it must still get the login hint.

**2. Extract shared CLI helpers into `src/vocky/cli/context.py`** to allow clean multi-module command registration without an app↔command import cycle. Move `CliContext`, `resolve_base_url`, `fail`, `cli_errors`, `DEFAULT_BASE_URL` there (context imports nothing from `app`/command modules). `app.py` imports them from `context` and **re-exports** `DEFAULT_BASE_URL` + `resolve_base_url` so the S1 test's `from vocky.cli.app import DEFAULT_BASE_URL, resolve_base_url` keeps working unchanged. `app.py` keeps `app`, the `--version`/`--base-url` callback, and `main()`, and at the bottom registers command modules: `from vocky.cli import auth; auth.register(app)`. Command modules import only from `context` + `config_store` + `client` → no cycle regardless of import order.

**3. New `src/vocky/cli/auth.py`** — four commands registered top-level via `register(app: typer.Typer) -> None` (`app.command("signup")(_signup)`, etc.), each body wrapped in `with cli_errors():`:
- **`vocky signup`** — `--email` (option; interactive prompt if omitted on a TTY) + password via a hidden confirm prompt, or `--password-stdin` to read one line from stdin (non-interactive / agent use — never put the password in argv). `make_client(use_stored_token=False).post("/auth/signup", json=..., auth=False)`. On `201`: `config_store.set_token(token)`, print `Signed up and signed in as <email>.` + `A workspace "<tenant.name>" was created for you automatically.` On `409` → `fail("An account with that email already exists — run \`vocky login\`.")`. On `400` → surface the server detail (e.g. password < 8 chars).
- **`vocky login`** — same `--email` / hidden-prompt / `--password-stdin` input. `post("/auth/login", ..., auth=False)`. On `200`: store token, print `Signed in as <email>.` On `401` (now `ApiError`, unauthenticated) → `fail("Incorrect email or password.")` (generic, no enumeration).
- **`vocky logout`** — best-effort `post("/auth/logout")` with the stored token (ignore any error — idempotent/`204`), then `config_store.clear_token()`, print `Signed out.` Friendly even when no token was stored.
- **`vocky whoami`** — if `config_store.get_token()` is `None` → `fail("Not signed in — run \`vocky login\`.")`; else `get("/auth/me")` and print email + tenant name(s). A 401 here (token sent but expired) flows through the client's session-expired hint.

## Files
- `src/vocky/cli/client.py` — token-aware 401 handling (small change to `request`/`_handle`).
- `src/vocky/cli/context.py` — **new**; extracted shared helpers.
- `src/vocky/cli/app.py` — import+re-export from `context`; register `auth` at the bottom.
- `src/vocky/cli/auth.py` — **new**; four commands + `register`.
- `tests/test_cli_auth.py` — **new**, small.

## Tests (keep small — one terse file)

`tests/test_cli_auth.py` with `typer.testing.CliRunner` + `httpx.MockTransport` + `VOCKY_CONFIG_DIR`→`tmp_path` (never the real `~`). Inject the mock transport by monkeypatching the client factory (e.g. patch `CliContext.make_client` to return `ApiClient(base_url, token=..., transport=MockTransport(handler))`). ~4 high-value cases:
- `signup` 201 → token stored + the "workspace created" line printed.
- `login` 401 → "Incorrect email or password", non-zero exit, **no** token stored.
- `logout` → token cleared (and fine when none was stored).
- `whoami` with no stored token → "run `vocky login`" without an HTTP call.

## Verification (run the code end-to-end)

Against a live local server (`make bootstrap` if not already up):
- `printf 'pw-at-least-8\n' | uv run vocky signup --email cli-$(date +%s)@example.com --password-stdin` → prints signed-in + auto-workspace line; the config file now holds a token (`0600`).
- `uv run vocky whoami` → shows the email + workspace.
- `uv run vocky login --email <same> --password-stdin` with a wrong password → "Incorrect email or password", exit 1.
- `uv run vocky logout` → "Signed out."; `whoami` then says run `vocky login`.
- `uv run pytest tests/test_cli_auth.py tests/test_cli_foundation.py` passes (S1 test still green).
- `python3 scripts/workflow.py validate` passes.

## Notes for the executor
- No auth backend change — client only. Do not touch `admin_assets/docs.json` or server code.
- Append a one-line **"Doc impact"** note to `phase.md` (the `vocky signup/login/logout/whoami` surface + `--password-stdin` for agents) for REVIEW to fold into `experience.md`. Do **not** run `doc-new-version`.
- Write `result.md`; append cross-slice notes (the `register(app)` pattern + `context.py` location, and the token-aware 401 contract) so S3/S4 follow the same structure. Do not commit or transition status.
