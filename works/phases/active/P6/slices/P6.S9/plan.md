# P6.S9 — PyPI packaging + publish · plan

> Slice `P6.S9` (implementation, risk medium → **executed by `slice-executor-high`**: the dep split touches
> dev + the backend Docker build + the lockfile). Makes `pip install vocky` / `uvx vocky` real. The actual
> `uv publish` is **operator-authorized** (PyPI token) — the executor stops before it. Read `phase.md`.

## Context

P5 built the `vocky` CLI as the agent-first surface (`uvx vocky` / `pip install vocky`, no website visit).
The CLI is **import-isolated**: `vocky/__init__.py` is trivial and every `vocky.cli.*` module imports only
`typer` + `httpx` + stdlib (plus the lightweight `vocky.smoke`, httpx-only). PyPI name `vocky` is **free**
(404). Operator chose the **lean-CLI split**.

## Edit — `pyproject.toml`

- **Split deps.** `[project.dependencies]` → core only: `httpx`, `typer` (keep pins). Move the rest into
  `[project.optional-dependencies] server = [alembic, greenlet, mcp[cli], pydantic-settings, psycopg[binary],
  redis, sqlalchemy, starlette, uvicorn[standard], python-multipart, argon2-cffi]` (same pins).
- **Keep dev working.** Add `[tool.uv] default-extras = ["server"]` (verify `uv` supports it; if not,
  **escalate** with the fallback — never leave `uv sync` unable to run the tests). Keep
  `default-groups = ["dev"]`. Plain `uv sync` must still install core + server + dev.
- **Enrich metadata**: product/CLI `description`; `keywords` (feedback, voice-of-customer, voc, saas, cli);
  `classifiers` (Development Status :: 3 - Alpha, Environment :: Console, Intended Audience :: Developers,
  Programming Language :: Python :: 3.12 / 3.13, Operating System :: OS Independent, Topic :: Software
  Development); `[project.urls]` Homepage `https://vocky.hi2vi.com`, Repository
  `https://github.com/leetusik/vocky`, Documentation = repo README/CLI guide. Keep MIT (SPDX
  `license = "MIT"` + `license-files = ["LICENSE"]` **iff** hatchling accepts it; else `{ text = "MIT" }`
  + the `License ::` classifier — not both). **No personal email** in `authors`.
- Keep all four `[project.scripts]`.

## Edit — backend `Dockerfile`

Add `--extra server` to **both** `uv sync` lines (`... --no-install-project --extra server` and
`... --no-dev --extra server`) — deterministic, don't rely on `default-extras` reaching `--no-dev`.

## Regenerate + docs

- `uv lock` → refresh `uv.lock` with the extras (commit it).
- If `README.md`'s install section implies `pip install vocky` yields the server, add a one-line note that
  self-hosting uses `pip install "vocky[server]"`. Minimal.

## Build + verify (NO publish)

- `uv lock` resolves; `uv sync` (dev) installs core+server+dev; **`uv run pytest` stays green**.
- `uv sync --extra server` resolves cleanly (proves the Docker dep path resolves locally).
- `uv build` → `dist/vocky-0.1.0.tar.gz` + `.whl`.
- **Lean-CLI proof:** `uvx --from dist/vocky-0.1.0-*.whl vocky --version` (and `--help`) succeed — the CLI
  runs from the wheel's **core** deps only.
- Wheel `METADATA`: `Requires-Dist: httpx…`/`typer…` unconditional; `Provides-Extra: server` with the heavy
  deps gated `; extra == "server"`.
- `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/vocky/json` → 404 (name free).
- `python3 scripts/workflow.py validate` passes.

## Publish — operator-gated

Stop at "built + verified" and return **`needs_operator`** with the publish instructions (wheel path,
`uv publish`, needs a PyPI token, name is free). **Do not run `uv publish` yourself** — publishing is
irreversible. The orchestrator sets S9 `pending` for the operator to publish.

## Docs impact

Append a **Doc impact** note to `phase.md`: dep split (core CLI vs `[server]` extra), backend Dockerfile
`--extra server`, PyPI metadata; `vocky` published (once done). REVIEW → `docs/current/operations.md` +
`experience.md`/`product.md`.

## Executor notes (high tier)

The split must not break dev/tests or the server image's dep set. If `uv default-extras` isn't supported or
the split can't keep `uv run pytest` green without a heavier change, **escalate**. Do packaging + build +
lean-CLI verify, then **stop and return `needs_operator`** — do not publish. Write `result.md`; append the
Doc-impact note to `phase.md`. Do not commit; do not transition status.
