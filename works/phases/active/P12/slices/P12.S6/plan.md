# Plan — P12.S6: Extend `ci.yml` with a Postgres-backed pytest job

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-mid` (risk `medium`).

**Reordered:** this slice was cut at `order 6` (post-launch) and the operator moved it to **3.5**, ahead of
the bring-up — see `phase.md` § *Operator decisions*. The reason is the whole point of the slice: the 108
DB-backed tests and P10's accounts-v2 migration have **never run on a runner**, so as originally ordered
`P12.S4`'s `alembic upgrade head` would have been the first execution of the full migration chain
anywhere, on production. This lands the signal first.

## Scope

Two additions to the **existing** `.github/workflows/ci.yml`. **Do not create a second workflow file** —
that file's own header comment (lines 9-14) says, verbatim, *"P12 is expected to add a job to this same
file, not start a new one"*, and names the two things it deliberately excluded. You are closing both.

1. A new job running the Python suite against a Postgres service container.
2. A `pnpm format:check` step added to the **existing** `web` job (`P12.S2` cleared the 14 formatting
   failures that made this impossible; `web/package.json:15` already defines the script).

Then update the header comment so the file stops describing exclusions that no longer exist.

## What the suite actually needs (verified — do not re-derive)

- **Two distinct databases.** `tests/conftest.py` reads `DATABASE_URL` (`:64`) and `TEST_DATABASE_URL`
  (`:80`, derived as `<basedb>_test` when unset). It rejects the run if the two rendered URLs are **string
  equal** (`:87-88`) or the test URL has no database name (`:95-96`).
- **The base database must already exist**, because conftest connects to it with psycopg autocommit and
  issues `CREATE DATABASE` for the test database only if absent (`:93-111`). The role therefore needs
  `CREATEDB` — the official image's default superuser has it; do not downgrade the role.
- **conftest runs alembic itself** — `command.upgrade(Config("alembic.ini"), "head")` at `:119`, with a
  **relative** path. So the job must run from the repo root: **give this job no `working-directory`.**
- **No Redis service container.** Every Redis touch in the suite is `fakeredis.aioredis.FakeRedis`
  injected by constructor (7 test files), the real client is lazy, and `redis_url` has a default.
- **`uv sync` alone is enough.** `pyproject.toml:89-90` sets `[tool.uv] default-groups = ["dev"]` and the
  dev group self-references `"vocky[server]"` (`:50-61`, with a comment saying exactly this), so a plain
  sync installs psycopg, alembic, sqlalchemy, pytest and the rest. `.python-version` pins `3.12` and uv
  honours it — no `setup-python` step needed.
- **Bare `uv run pytest` from the repo root is the whole invocation.** `[tool.pytest.ini_options]` is just
  `asyncio_mode = "auto"` and `testpaths = ["tests"]`; there is no `addopts`, no marker set, no coverage
  wiring. Do not add flags without a reason, and do not add coverage (out of scope).

**Fresh evidence from `P12.S3` (2026-08-04):** the full suite was run against a real Postgres in an
executor sandbox and returned **215 passed, 0 failures/errors**. So the suite is genuinely green when a
database is reachable — a red first CI run means the *workflow wiring* is wrong, not the tests.

## The new job

Match the file's house style exactly: a human-readable `name:` on the job and on every step, block-scalar
`run:` with `shell: bash` and `set -euo pipefail` as the first line, `runs-on: ubuntu-latest`,
`actions/checkout@v4`.

- **Service container:** `postgres:17` — pin it to match production (`compose.prod.yml:37`) and dev
  (`docker-compose.yml:16`). Env `POSTGRES_DB: vocky`, `POSTGRES_USER: vocky`, `POSTGRES_PASSWORD: vocky`
  (the shapes `.env.example` documents). Map `5432:5432` — **not** 55432, which is only the local
  host-publish port.
- **Health options are mandatory**, not optional polish: conftest connects at session start with no retry
  loop, so without a health gate the job flakes on the first psycopg connect. Use the standard
  `--health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5`.
- **Job env:**
  - `DATABASE_URL: postgresql+psycopg://vocky:vocky@localhost:5432/vocky`
  - `TEST_DATABASE_URL: postgresql+psycopg://vocky:vocky@localhost:5432/vocky_test`
  Set **both** explicitly even though conftest can derive the second — explicit is what the guard checks
  and what a reader needs. Note `DATABASE_URL` has no default in `config.py` and `.env` is gitignored, so
  the job env is the only source; a missing var surfaces as a pydantic `ValidationError` at import, which
  is a confusing failure — a comment in the workflow is worth it.
- **Steps:** checkout → install uv (`astral-sh/setup-uv`, pinned to a current major; this is the repo's
  first use of it, so add a one-line comment saying `.python-version` drives the interpreter) →
  `uv sync --frozen` (`uv.lock` is committed) → `uv run --no-sync pytest`. That mirrors the `Dockerfile`'s
  `uv sync --frozen` idiom.
- **Add `timeout-minutes`** (20 is a sane first guess) — the suite is serial, session-scoped and
  DB-backed, and an unbounded hang on a first-ever run is the failure mode to avoid.
- The workflow-level `on:` already covers `push: [main]` and `pull_request`; inherit it. Do not add a
  `concurrency` block — `ci.yml` deliberately has none.

## The prettier gate

Add one step to the **existing `web` job**, after `Install dependencies` and alongside `Lint` /
`Typecheck` / `Test`: `pnpm format:check`. That job already sets `working-directory: web` and has pnpm
installed, so no new job and no second install. Keeping the check inside `web/` matters —
`web/.prettierignore` excludes `public/`, which is what protects the served `SKILL.md` byte-parity gate
that the `skill-parity` job asserts.

## The header comment

`ci.yml:9-14` currently lists `prettier --check` and `uv run pytest` as deliberate exclusions and says P12
will add them. Rewrite that passage so it describes the file as it now is. This repo comments heavily and
precisely; a stale comment here is a review finding.

## Boundaries

- Files you may change: `.github/workflows/ci.yml` only. If you find you need a second file, stop and
  explain why rather than adding one.
- Do **not** touch `.github/workflows/deploy-production.yml` (`workflow_dispatch`-only, main-guarded — it
  is not a CI gate and is out of scope).
- Do not change any test, any source file, `pyproject.toml`, `uv.lock`, or `Makefile` to make CI pass. If
  the suite needs a change to run on a runner, that is a finding to report, not a fix to make here.
- Do not edit anything under `docs/`, do not run `doc-new-version`, do not commit, do not run any
  `scripts/workflow.py` state command.

## Validation — and be honest about its limits

**You cannot execute a GitHub Actions run from here, and it will not run on push either: the repo has ~57
unpushed commits, and the push is an operator gate inside `P12.S4`.** So this slice's proof is static plus
a local equivalence check. Do all of these and report actual output:

1. **YAML parses:** `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`.
   (`actionlint` and `shellcheck` are **not installed** in this sandbox — do not plan around them; if you
   find one available, use it and say so.)
2. **Local equivalence:** run the suite exactly as the job will, from the repo root, with the two job env
   vars set to a locally reachable Postgres — `DATABASE_URL=… TEST_DATABASE_URL=… uv run pytest`. Report
   the counts. `P12.S3` saw 215 passed; a database was reachable in that sandbox. If none is reachable in
   yours, say so plainly and report what you could and could not prove.
3. **The prettier gate is green now:** `cd web && pnpm format:check`.
4. Re-read the finished `ci.yml` end to end and confirm: no `working-directory` on the pytest job, both
   env vars present, health options present, the image pinned to `postgres:17`, and the header comment no
   longer claims either exclusion.

## Deliverables

- `result.md` (free-form): the job as landed, every decision and its reason, the verbatim validation
  output, an explicit statement of **what remains unproven until the first real runner execution**, and
  the most likely first-run failure modes with the fix for each.
- Notes appended to `phase.md` § *Findings & Notes*: that `ci.yml` now gates pytest + prettier, the exact
  env contract the job depends on, and — importantly for `P12.S4` — that **the push at S4 triggers this
  workflow's first-ever execution**, so S4 should expect to watch it and iterate.
- A **Doc impact** line in `phase.md` § *Doc impact*: `operations.md`'s `ci.yml` section (which records
  the two exclusions, and the prettier failure count) is now stale — the gate covers the Python suite and
  formatting. `P12.REVIEW` consolidates it.
