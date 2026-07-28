# P11.S2 — CLI: `VOCKY_API_TOKEN` resolution + `vocky capture` over `/api/feedback`

## Why

The phase's headline promise is that **two environment variables are the whole agent contract**. Today
`VOCKY_BASE_URL` exists and `VOCKY_API_TOKEN` does not exist anywhere in the tree, and the CLI has **no
capture command at all** — so a `vk_` key has no CLI consumer and the install line has nothing to be
installed *for*. This slice closes both gaps.

A `vk_` key authorizes **only** `/api/*` and `/mcp`. Every existing CLI command talks to `/app/*` with a
**session** token (`src/vocky/cli/projects.py:7` states the invariant outright). `capture` is the first
command on the other side of that line, and the whole design problem is keeping the two credentials from
touching each other.

## Design decisions (settled here — implement these, do not re-litigate)

### 1. Token resolution: env var only, no `--token` flag

Add a **module-level** `resolve_api_token(...)` in `src/vocky/cli/context.py`, directly beside
`resolve_base_url` (`context.py:66-84`) and mirroring its shape. Precedence is exactly two tiers:

```
VOCKY_API_TOKEN  →  (nothing: fail with a message naming the env var)
```

- **No `--token` flag.** `src/vocky/cli/auth.py:579-587`-style reasoning already exists in this repo for
  `--password`: argv is world-readable via `ps` and lands in shell history. A `vk_` key is a bearer
  credential with the same exposure. Say this in the function's docstring.
- **No config-store persistence.** Do **not** add an `api_token` key to `config_store`. Two reasons:
  `clear_token()` (`config_store.py:113-118`) pops only `"token"`, so a persisted `vk_` key would survive
  `vocky logout` — a leak-shaped bug; and the phase's contract is deliberately env-var-based.
- **Put it on the module, not on `CliContext`.** `CliContext` is built once in `app.py:76` and its only
  credential path is `config_store.get_token()` — the session token. Resolving the `vk_` key onto
  `ctx.obj` is precisely the conflation to avoid. Resolve it **inside the `capture` command body**.
- Read it the same way `resolve_base_url` reads its env var: `os.environ.get("VOCKY_API_TOKEN", "").strip()`,
  treating empty/whitespace as absent. No new imports are needed — `context.py` already imports `os`.
- Failure message must name the variable and point at where a key comes from, e.g.
  `VOCKY_API_TOKEN is not set — mint a key with `vocky keys mint` and export it.`

### 2. Client seam: `context.make_client(token=api_token, use_stored_token=False)`

Use exactly this call. Do **not** construct `ApiClient(...)` directly in `capture.py`. Two things depend
on it:

- `use_stored_token=False` **structurally guarantees** the session token can never be sent on a capture
  call, rather than relying on care.
- The CLI test suite stubs HTTP by monkeypatching `CliContext.make_client` (`tests/test_cli_projects.py:35-46`).
  A directly-constructed `ApiClient` would bypass that stub and the tests could not intercept it.

`ApiClient._handle` already treats **202 as success** (`client.py:134`, `response.is_success`) and returns
the parsed JSON, so `post("/api/feedback", json=…)` returns
`{"request_id": …, "accepted_at": …, "status": "accepted"}` with no special-casing.

### 3. The 401 trap — thread an override through the client

`src/vocky/cli/client.py:146` converts **any** 401-with-token into
`CliError("Not signed in — run `vocky login`.")`. For `capture` that message is actively wrong: the user
is not signed out, their `VOCKY_API_TOKEN` is wrong or revoked. And because a 401 is raised as `CliError`
(not `ApiError`), the per-command `exc.status_code` remapping idiom used at `projects.py:214-225` **cannot**
catch it.

Fix it at the source: add a **keyword-only** `unauthorized_message: str | None = None` parameter and thread
it from the public verb methods (`post`, and `request` / whatever they delegate to) into `_handle`, where:

```python
if response.status_code == 401 and token_sent:
    raise CliError(unauthorized_message or "Not signed in — run `vocky login`.")
```

The default preserves today's behavior for every existing caller — this must be a **no-behavior-change**
edit for `auth.py`, `projects.py`, and `feedback.py`. `capture` passes something like
`"Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked)."`

Do **not** solve this by string-matching the existing error message in the command.

### 4. Command shape: a top-level `vocky capture`

`usage` is registered as a bare top-level command (`projects.py:307`) — that is the precedent. `capture` is
top-level, not a sub-app.

**Message** is a positional `typer.Argument` (matching `projects create NAME`), with one idiom added: if
the value is exactly `-`, read the entire message from stdin (`sys.stdin.read()`, then strip the trailing
newline). That lets an agent pipe a multi-line quote without fighting shell quoting, and it costs one
branch. There is no `--token-stdin` to collide with, because there is no token flag.

**Options** — all `typer.Option` with `metavar=` and sentence-case `help=` ending in a period, following
`projects.py`'s idiom:

| Option | Type | Maps to | Notes |
|---|---|---|---|
| `--product` | `str` | `source.product` | **Required.** Non-blank — the API rejects blank (`capture.py:275`). |
| `--integration` | `str \| None` | `source.integration` | Optional. |
| `--value` | `int \| None` | `feedback_value` | Help: `1 = liked, 2 = disliked.` |
| `--comment` | `str \| None` | `comment` | |
| `--tag` | `list[str]` | `tags` | Repeatable. Omit the key entirely when empty. |
| `--session-id` | `str \| None` | `session_id` | Groups a conversation. |
| `--user-id` | `str \| None` | `user_id` | |
| `--project` | `str \| None` | `project` | REST-only extra: destination project name, honored **only** for an org-level key; project-bound keys ignore it. Say that in the help. |

**Build the body by hand** — omit every key the user did not supply rather than sending explicit nulls.
`source` is the only nested object:

```python
payload: dict[str, Any] = {"message": message, "source": {"product": product}}
if integration: payload["source"]["integration"] = integration
# … then each optional top-level key, only when provided
```

The in-tree reference for the exact shape is `src/vocky/smoke.py:107-131`.

**Output** on success — plain `typer.echo`, no rich (the CLI has no rich, no shared formatter, and no
`--json` flag anywhere; do not introduce one):

```
Captured — request_id <full id>
```

Print the id in full: it is a handle the user may quote in a support thread, the same reasoning as
`projects.py:71-73`.

**Body shape**: wrap in `with cli_errors():`, take `context: CliContext = ctx.obj`, use the client as a
context manager, and render **outside** the `with client` block but inside `cli_errors()` — exactly
`projects.py:80-92`.

**Docstring** (which becomes the command help) must state that this command authenticates with the `vk_`
ingest key from `VOCKY_API_TOKEN` and **not** with the stored session token — the mirror of the invariant
comment at `projects.py:7`.

### 5. Registration

In `src/vocky/cli/app.py`, add to the deferred import block at `:85-94` (alphabetical — `capture` sorts
first) and call `capture.register(app)`. `register()` follows `projects.py:294-307`:
`app.command("capture")(_capture)`.

### 6. Close the loop at `keys mint`

`_keys_mint` (`projects.py:117-150`) prints the plaintext key alone on the final stdout line so it is
copy-pasteable — the only place a user ever sees it. Add **one** hint line **before** that final key line
(never after it — the key must stay last), pointing at the export, e.g.:

```
Export it for `vocky capture` and agent skills:  export VOCKY_API_TOKEN=<the key below>
```

Adjust the existing `tests/test_cli_projects.py` mint assertions if they pin exact output; keep the change
minimal.

### 7. Version bump

`pyproject.toml:7` is still `0.1.0`, which predates P10's org keys and this slice. Bump to **`0.2.0`** and
re-run `uv lock` (the lockfile carries the project version). Note that `--version` reads
`importlib.metadata.version("vocky")` (`app.py:51-54`) — **installed** metadata, so the new number only
shows after a reinstall; say so in `result.md` rather than treating a stale in-place number as a failure.

## Import isolation — the one thing that must not break

`vocky.cli.*` may import **only** typer / httpx / stdlib / `vocky.smoke`. The lean install (httpx + typer,
~15 packages) depends on it, and a violation fails silently at install time, not at test time.

**Do not `from vocky.capture import …`.** That is the single most likely mistake in this slice, because
`src/vocky/capture.py` is where the schema lives — and it imports pydantic. Hand-build the dict; do not
import the models, the field list, or any validator. Likewise avoid `vocky.config`, `vocky.db`,
`vocky.api`, `vocky.app_api`, `vocky.auth`, `vocky.feedback.*`, `vocky.persistence.*`,
`vocky.tools.*`, `pydantic`, and `rich`.

Guard: `uv build && uvx --no-cache --from dist/vocky-0.2.0-py3-none-any.whl vocky --version`.

## Tests — terse, matching the house idiom

New file `tests/test_cli_capture.py`. Use `typer.testing.CliRunner` (never subprocess) and
`httpx.MockTransport` injected by monkeypatching `CliContext.make_client` — copy the `_stub_api` helper
shape from `tests/test_cli_projects.py:35-46`, and copy the `config_env` fixture, **adding**
`monkeypatch.delenv("VOCKY_API_TOKEN", raising=False)` so a developer's real key can never leak into a
test run.

Three tests, no more:

1. **Happy path** — with `VOCKY_API_TOKEN` set, the handler asserts `POST /api/feedback`, the body's
   nested `{"source": {"product": …}}`, that `Authorization` is `Bearer vk_test…` (the `vk_` key, **not**
   the stored session token), and returns `202 {"request_id": …, "accepted_at": …, "status": "accepted"}`.
   Assert `exit_code == 0` and that the request id appears in stdout.
2. **Missing token** — `VOCKY_API_TOKEN` unset → non-zero exit, and stderr/output names `VOCKY_API_TOKEN`.
   No HTTP call is made.
3. **401** — the handler returns `401` → the message names `VOCKY_API_TOKEN` and does **not** say
   "run `vocky login`".

Assert requests **inside** the handler and use `assert result.exit_code == 0, result.output`, per
`tests/test_cli_projects.py:49-72`.

## Docs

Update `docs/cli.md`:

- Add `VOCKY_API_TOKEN` to the environment section beside `VOCKY_BASE_URL` (`docs/cli.md:24-40`), stating
  plainly that it holds a `vk_` **ingest** key and is used **only** by `vocky capture`, while every other
  command uses the stored session token.
- Add a short `capture` section with a real invocation and the two-export quickstart.
- `docs/cli.md:72` says everything sends the session token as `Authorization: Bearer` — that sentence is
  now false. Correct it.

Do **not** touch the stale "PyPI publishing is P6" line at `docs/cli.md:11` or `README.md:50` — those are
recorded in `phase.md` as `P11.S3`/`P11.S4` work.

**Doc impact**: this changes durable truth (a new CLI command + a new env var in the agent contract).
Append **one line** to the `## Doc impact` section of `works/phases/active/P11/phase.md` naming the
affected docs (`experience`, `product`, and/or `operations`) for the phase review to consolidate. Do
**not** run `doc-new-version`.

## Validation

From the repo root:

1. `uv run pytest tests/test_cli_capture.py -q` → all pass.
2. `uv run pytest tests/test_cli_foundation.py tests/test_cli_auth.py tests/test_cli_projects.py tests/test_cli_feedback.py -q`
   → all pass. The `unauthorized_message` default must have changed nothing here.
3. `uv run pytest -q` → compare against the **pre-slice baseline**. The suite has ~108 pre-existing
   `psycopg.OperationalError` errors when no Postgres is running (documented in `P6.S9`'s result); that
   count must not grow. Record both numbers in `result.md`.
4. `uv run vocky capture --help` → renders; `uv run vocky --help` shows `capture` in the command list.
5. `uv lock` → exits 0 after the version bump.
6. `uv build && uvx --no-cache --from dist/vocky-0.2.0-py3-none-any.whl vocky --version` → prints `0.2.0`
   and resolves **~15 packages** (httpx + typer + transitives only). This is the lean-install guard; if it
   pulls sqlalchemy/uvicorn/psycopg, an import isolation violation crept in — fix it before returning.
7. `grep -rn "^from vocky\.\|^import vocky\." src/vocky/cli/` → only `vocky.cli.*` and
   `vocky.smoke` appear.

No live server is available and none is needed — every test stubs the transport. State in `result.md` that
`capture` has **not** been exercised against a real running API, and that the end-to-end proof lands in
P12's live smoke.

## Out of scope

- No backend change. `POST /api/feedback`'s contract is not touched.
- No `/mcp` work — the skill will mention it as an alternative transport in `P11.S4`.
- No install line, no installer, no landing change.
- No `--json` output flag, no rich, no new dependency of any kind.
- No `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S2/result.md` from scratch (free-form): the command surface as
it landed, the `unauthorized_message` threading and which call sites it touched, the verbatim output of
each validation command including both pytest baselines and the lean-install package count, and what was
**not** behaviorally proven. Append durable cross-slice notes to `works/phases/active/P11/phase.md` —
`P11.S4` will author the end-user skill directly against this command's surface, so record the exact final
option names and the exact success/error output strings. Do not commit and do not change any slice or
phase status.
