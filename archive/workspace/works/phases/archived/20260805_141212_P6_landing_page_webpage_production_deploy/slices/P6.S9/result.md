# P6.S9 — PyPI packaging + publish · result

**Status: `done` (packaging only — the publish moved to P11).**

> **SCOPE CHANGE, 2026-07-28 (operator).** The original status was `needs_operator`, waiting on `uv publish`.
> That gate is withdrawn and **the publish is no longer part of P6**. Two things changed after this slice ran:
> the production bring-up moved out of P6 into **P12**, so nothing left in P6 needs a published package; and
> **P11** (frictionless onboarding) was created to own the install story, which has not yet chosen between PyPI
> and a `curl | bash` installer. Publishing here would decide that by default — and would ship a `0.1.0` that
> **P10** (org-level keys, `--project`, repo-basename project resolution) and **P11** (`VOCKY_API_TOKEN`) both
> change, so the version anyone following the landing page installs would be obsolete on arrival.
>
> This slice's actual deliverable — the lean-CLI / `server` extra split, the PyPI metadata, and the sdist-bloat
> fix — is complete and verified below. **The publish instructions in the section below are retained verbatim as
> the hand-off to P11**, not as a pending action on P6.
>
> Still open, and deliberately left to the operator as a standalone call independent of any phase: the PyPI name
> `vocky` was **free** (404) when this slice ran. Reserving it is cheap insurance and is not gated on P11.

## What changed

### `pyproject.toml` — lean-CLI dependency split + PyPI metadata
- **Core deps** (`[project.dependencies]`) reduced to `httpx` + `typer` (pins kept). Everything else moved
  to `[project.optional-dependencies] server` (alembic, greenlet, mcp[cli], pydantic-settings,
  psycopg[binary], redis, sqlalchemy, starlette, uvicorn[standard], python-multipart, argon2-cffi — same pins).
- **Metadata enriched:** product/CLI `description`; `keywords` (feedback, voice-of-customer, voc, saas, cli);
  `classifiers` (Development Status :: 3 - Alpha, Environment :: Console, Intended Audience :: Developers,
  Programming Language :: Python :: 3.12 / 3.13, Operating System :: OS Independent, Topic :: Software
  Development — **no** `License ::` classifier, since SPDX is used); `[project.urls]` Homepage
  `https://vocky.hi2vi.com`, Repository `https://github.com/leetusik/vocky`, Documentation → the CLI guide
  (`.../blob/main/docs/cli.md`). Author left as `{ name = "Vocky" }` (no personal email).
- **License:** SPDX form `license = "MIT"` + `license-files = ["LICENSE"]` — hatchling>=1.27.0 accepted it
  (wheel METADATA emits `License-Expression: MIT` + `License-File: LICENSE`). Fallback (`{ text = "MIT" }` +
  classifier) not needed.
- All four `[project.scripts]` kept (`vocky`, `vocky-server`, `vocky-smoke`, `vocky-worker`).

### `Dockerfile` (backend) — deterministic server deps
- Added `--extra server` to **both** `uv sync` lines (`--no-install-project --extra server` and
  `--no-dev --extra server`) so the server image installs the full stack independent of any default-extras.

### `uv.lock` — regenerated
- `uv lock` refreshed the lockfile; the 11 server deps are now gated behind the `server` extra marker
  (11 `extra == "server"` markers present).

### `README.md` — one-line install note
- Added, after the Install options: once published, `pip install vocky` / `uvx vocky` install the lean CLI
  (httpx + typer only); self-hosting the full server uses the `server` extra — `pip install "vocky[server]"`.

## Deviations from `plan.md`

1. **`[tool.uv] default-extras` is NOT supported by the installed uv (0.8.14)** — `uv lock` rejected it as an
   unknown field in `[tool.uv]` (accepted fields include `default-groups` but not `default-extras`; that
   field landed in a later uv release). The plan said to escalate the fallback if `default-extras` isn't
   supported, but this slice is executed at the **high tier** (never escalates), and the plan's *intent* —
   "plain `uv sync` must still install core + server + dev" — is cleanly achievable another way. **Fix:**
   self-reference the project's own extra in the dev dependency group (`"vocky[server]"` in
   `[dependency-groups] dev`, which is a default group). A plain `uv sync` now installs core + server + dev
   and the suite stays green; dependency groups are never part of built dist metadata, so the published
   wheel/sdist stay lean (server only ever appears as a `; extra == "server"` gate). This is the standard
   uv 0.8.x idiom for "dev needs an extra."
2. **Added `[tool.hatch.build.targets.sdist]` include-list** (not in the plan). An unconstrained `uv build`
   produced a **~680 MB sdist** because hatchling's default sdist selection does not honor the nested
   `web/.gitignore`, so it swept in `web/node_modules` + the `.next` turbopack cache (13,254 files). That
   sdist is not PyPI-publishable (>100 MB limit), which would defeat "make vocky publishable." Restricting
   the sdist to root-anchored `["/src/vocky", "/README.md", "/LICENSE"]` (anchoring matters — bare
   `README.md`/`LICENSE` globs otherwise matched thousands of nested node_modules files) brings the sdist to
   **79 KB**. The wheel is `src/vocky` only and was unaffected throughout (95 KB).

## Verification (actual output)

| Step | Command | Result |
|---|---|---|
| Lockfile | `uv lock` | Resolved 64 packages, exit 0, no warnings |
| Dev sync | `uv sync` | OK; server deps import (`sqlalchemy, alembic, redis, starlette, uvicorn, psycopg, argon2, mcp, pydantic_settings, greenlet, multipart` → "server deps import OK") |
| Full suite | `uv run pytest -q` | **79 passed, 108 errors** — the 108 are `psycopg.OperationalError` (no Postgres in sandbox: port 55432 closed, Docker daemon unavailable per S4/S5 findings) |
| **Baseline** | stash split → `uv sync` + `uv run pytest -q` on pre-split HEAD | **79 passed, 108 errors** — *identical* → the errors are pre-existing (no DB), **not** caused by the split. Split restored (`git stash pop`). |
| Server path | `uv sync --extra server` | Resolved 64, Audited 61, exit 0 (proves the Docker dep path resolves locally) |
| Build | `uv build` | Built `dist/vocky-0.1.0.tar.gz` (79 KB) + `dist/vocky-0.1.0-py3-none-any.whl` (95 KB) |
| **Lean-CLI proof** | `uvx --no-cache --from dist/vocky-0.1.0-*.whl vocky --version` | `0.1.0` — installed **15 packages** (httpx + typer + transitives only; no sqlalchemy/alembic/uvicorn/psycopg). `--help` also renders the full command tree. |
| Wheel METADATA | zip-inspect `*.whl` METADATA | `Requires-Dist: httpx…`/`typer…` **unconditional**; `Provides-Extra: server`; all 11 heavy deps gated `; extra == 'server'`; `License-Expression: MIT` + `License-File: LICENSE`; keywords/classifiers/Project-URLs present |
| PyPI name | `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/vocky/json` | **404** — name `vocky` is free |
| State integrity | `python3 scripts/workflow.py validate` | `Workflow validation passed.` |

The full pytest suite could not exercise the 108 DB-backed tests in-sandbox (no Postgres / no Docker daemon —
consistent with the S4/S5 findings); the baseline check proves the split changed nothing here (identical
79/108 before and after). Behavioral DB validation lands at S10 / CI, as with the other P6 deploy slices.

## Publish — hand-off to P11 (do NOT run here; no longer a P6 gate)

Everything is built and verified; publishing is irreversible and needs a PyPI token. **P11 decides whether this
runs at all** (PyPI vs a `curl | bash` installer). If P11 picks PyPI, this is the procedure — and note the
version will not be `0.1.0` by then, since P10 and P11 both change the CLI:

1. Artifacts are in `dist/`: `dist/vocky-0.1.0-py3-none-any.whl` (95 KB) + `dist/vocky-0.1.0.tar.gz` (79 KB).
2. The name `vocky` is **free** on PyPI (re-confirmed: `curl -s -o /dev/null -w '%{http_code}'
   https://pypi.org/pypi/vocky/json` → `404`).
3. Publish with a PyPI API token:
   ```sh
   uv publish            # uploads everything in dist/ (defaults to https://upload.pypi.org/legacy/)
   # token via UV_PUBLISH_TOKEN=pypi-... or `uv publish --token pypi-...`
   ```
   (Optionally test-drive on TestPyPI first: `uv publish --publish-url https://test.pypi.org/legacy/`.)
4. After a successful publish, confirm `uvx vocky --version` from a clean machine and drop the README's
   "PyPI publishing is P6; until then…" caveat.

## Doc impact (appended to `phase.md`)
See the "Doc impact" note added for P6.S9 in `phase.md`.
