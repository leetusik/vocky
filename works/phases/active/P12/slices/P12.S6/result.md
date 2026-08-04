# Result — P12.S6: Extend `ci.yml` with a Postgres-backed pytest job

## What landed

One file changed, `.github/workflows/ci.yml` (no second workflow file created, `deploy-production.yml`
untouched). Three changes, exactly the slice's scope:

1. **New `pytest` job** — Postgres service container (`postgres:17`, matching `compose.prod.yml`/
   `docker-compose.yml`), `uv run pytest` against it.
2. **`Format check` step** added to the existing `web` job, after `Test`, running `pnpm format:check`
   (`web/.prettierignore` already excludes `public/`, so the served `SKILL.md`/`install.sh` gate is
   untouched by adding this inside the `web` job's `working-directory: web`).
3. **Header comment rewritten** — no longer describes the two now-closed exclusions; states what the
   file checks today (skill parity, web lint/typecheck/vitest/prettier, installer syntax, Python tests
   against Postgres).

## Decisions and why (mapped to the plan's "what the suite needs" section)

- **No `working-directory` on the `pytest` job** — `tests/conftest.py` runs `alembic upgrade head` with a
  relative path to `alembic.ini`; the job runs from the repo root by omission (documented with a comment).
- **`ports: [5432:5432]`**, not `55432:5432` — the plan is explicit that `55432` is only this workspace's
  local host-publish port; the job's own `DATABASE_URL`/`TEST_DATABASE_URL` point at `localhost:5432`
  inside the runner's network namespace, where the service container is reachable directly (GitHub's
  service-container networking maps the container port to the same host port on the job's `ubuntu-latest`
  runner, not through Docker's usual host-side remap).
- **Both `DATABASE_URL` and `TEST_DATABASE_URL` set explicitly**, pointing at `vocky` and `vocky_test`
  respectively on the same server — matches the two-distinct-databases contract `conftest.py:64-96`
  enforces (rejects if string-equal, rejects if the test URL has no db name). A comment next to the block
  explains why both are required rather than letting the second derive, since `config.py` gives
  `DATABASE_URL` no default and `.env` is gitignored — a missing var here would otherwise surface as an
  opaque pydantic `ValidationError` at import time on a runner with no other diagnostic.
- **Health options are the standard five-liner** (`pg_isready`, `10s` interval, `5s` timeout, `5` retries)
  — mandatory per the plan, since conftest's session-scoped Postgres connect has no retry loop of its own.
- **`POSTGRES_USER`/`POSTGRES_DB`/`POSTGRES_PASSWORD` all `vocky`** — the official image's default
  superuser (implicit, since `POSTGRES_USER` is set) carries `CREATEDB`, which conftest needs to issue
  `CREATE DATABASE vocky_test` when it's absent. No role was downgraded.
- **`uv sync --frozen` then `uv run --no-sync pytest`** — mirrors the repo's own `Dockerfile` idiom named
  in the plan; `--frozen` respects the committed `uv.lock` without rewriting it, `--no-sync` on the pytest
  invocation avoids a redundant second resolve.
- **`astral-sh/setup-uv@v9`** — the plan asked for "a current major" without naming one, since this is the
  action's first use in the repo. This sandbox has outbound network access, so I queried GitHub's releases
  API live (`api.github.com/repos/astral-sh/setup-uv/releases/latest`) rather than guessing from training
  data staleness, and got `v9.0.0` as the current latest tag — pinned to `@v9`. No `setup-python` step: uv
  reads `.python-version` (`3.12`) itself.
- **`timeout-minutes: 20`** on the job, per the plan's "sane first guess" for a serial, session-scoped,
  DB-backed suite on its first-ever runner execution.
- **No `concurrency` block added** — `ci.yml` deliberately has none; the workflow-level `on:` (`push:
  [main]` + `pull_request`) is inherited by the new job with no changes.
- **No Redis service container** — confirmed by running the full suite locally (below): 0 Redis-related
  failures, consistent with the plan's `fakeredis` finding.

## Validation — actual output

**1. YAML parses.**
`python3 -c "import yaml, ..."` failed in the bare sandbox interpreter (`ModuleNotFoundError: No module
named 'yaml'` — no PyYAML outside the project's uv-managed venv). Ran it through the project's own
environment instead, which does carry PyYAML as a transitive dev dependency: `uv run python3 -c
"import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"` → `YAML OK`. This is
a strictly stronger check than the plan's literal invocation (same parser, same file), just run through
`uv run` because the bare `python3` on this machine has no PyYAML installed. `actionlint`/`shellcheck` are
confirmed **not installed** (`which actionlint shellcheck` → both "not found") — not used, as the plan
anticipated.

**2. Local equivalence — the pytest job's exact invocation, against a locally reachable Postgres.**
A Postgres container was already running in this sandbox from an earlier slice (`vocky-postgres-1`,
`postgres:17`, published on `127.0.0.1:55432`, user/db/password all `vocky` — matches `docker-compose.yml`'s
defaults). Ran:

```
DATABASE_URL="postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky" \
TEST_DATABASE_URL="postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky_test" \
uv run pytest
```

Result: **215 passed in 9.43s, 0 failures, 0 errors** — same count `P12.S3` reported. All 29 test files ran
(the `-vv` module summary shows every file with all-dots output, including the DB-heavy ones:
`test_accounts_persistence`, `test_admin_api`, `test_capture_validation`, `test_persistence`,
`test_worker`, etc.). This proves the suite genuinely is green when a Postgres is reachable and reachable
via exactly the two env vars the job sets — it does **not** prove the GitHub-hosted service-container
plumbing itself (see "What remains unproven" below).

**3. Prettier gate is green now.**
`cd web && pnpm format:check` → `Checking formatting... All matched files use Prettier code style!` (exit
0). Confirms `P12.S2`'s sweep left the gate this slice turns on already passing.

**4. Re-read `ci.yml` end to end.** Confirmed all five plan requirements:
- No `working-directory` on the `pytest` job — absent from its block.
- Both env vars present — `DATABASE_URL` and `TEST_DATABASE_URL` under the job's `env:`.
- Health options present — `pg_isready` / `10s` / `5s` / `5` under the service's `options:`.
- Image pinned to `postgres:17` — service `image:` field.
- Header comment no longer claims either exclusion — rewritten, no mention of "deliberately excluded",
  `prettier --check`, or "P12 is expected to add".

## What remains unproven until the first real runner execution

Nothing here executed inside an actual GitHub Actions runner — there is no such thing available from this
sandbox, and per the plan/phase notebook the workflow will not fire on push either, because the push is a
deliberate operator gate inside `P12.S4` and 57 commits are still unpushed. So the following stay
unproven until that first real run:

- **GitHub-hosted service-container networking specifically.** Local equivalence used a Docker container on
  a real Docker Engine; a GitHub-hosted runner's service-container feature works differently under the
  hood (it maps the container's exposed port onto the *same* port number on the job's own network
  namespace via a `docker create --network` wiring, not the local `-p 55432:5432`-style host remap this
  sandbox used). `localhost:5432` should resolve correctly per GitHub's own documented behavior for
  service containers with a `ports:` mapping, but that specific mechanism was not exercised here.
- **Runner-side `uv sync --frozen` from a clean image.** This sandbox already had a warm `uv` cache and a
  populated `.venv`; a fresh `ubuntu-latest` runner does a cold install of every dependency (psycopg's
  binary wheel, sqlalchemy, alembic, the full `vocky[server]` closure) — not exercised here.
- **`astral-sh/setup-uv@v9`'s actual behavior on this repo** — its Python-version detection from
  `.python-version`, its cache defaults, and its interaction with `uv sync --frozen` were not exercised;
  only the plan's stated contract (uv honours `.python-version`) is being trusted.
- **Total job wall-clock** against the `timeout-minutes: 20` budget — the local run was ~9.4s for the test
  phase, but `uv sync --frozen` from cold plus the Postgres health-gate wait are both unmeasured on a
  runner; 20 minutes is a guess with generous headroom, not a measured budget.
- **Whether `pull_request` events from a fork** (if this repo ever receives one) have any permission
  wrinkle with the `services:` block — not applicable today since this is a single-contributor repo, noted
  only for completeness.

## Likely first-run failure modes and the fix for each

1. **Service-container port/health timing mismatch** — if GitHub's service networking doesn't expose
   `localhost:5432` as expected, pytest's first connect fails immediately with `psycopg.OperationalError`
   despite the health gate passing. Fix: confirm via the job's own log which host/port `pg_isready`
   actually checked, adjust `ports:` or move to service-name-based host (`postgres:5432`, GitHub's DNS
   alias) if the direct `localhost` mapping doesn't hold on this runner image.
2. **Cold `uv sync --frozen` dependency-build failure** — `psycopg[binary]` or another compiled wheel not
   available for the runner's exact platform, forcing a source build that fails for a missing system
   library (e.g. libpq headers). Fix: add the relevant `apt-get install` step, or switch to a pure-Python
   psycopg variant if the project's `pyproject.toml` allows it (out of scope to decide here — a `fix`
   slice's call).
3. **`uv.lock` platform-lock drift** — if `uv.lock` was generated/frozen on a different platform (e.g. this
   macOS sandbox) without cross-platform resolution markers, `--frozen` sync on Linux could fail to
   satisfy a marker. Fix: regenerate `uv.lock` with `uv lock` on/for the Linux target, or verify
   `pyproject.toml`'s resolution already covers `linux` (this is a `uv.lock`/`pyproject.toml` change,
   explicitly out of this slice's bounds per the plan — report only).
4. **`alembic upgrade head` failing against a genuinely fresh database** — this is the actual point of
   moving this slice ahead of the bring-up per the phase notebook's Operator decision 2: the 108 DB-backed
   tests and the full P10 accounts-v2 migration chain have never executed against a database that didn't
   already exist from a prior local dev session. My local run reused a long-lived `vocky-postgres-1`
   container (up 3 weeks); the runner's Postgres is created fresh every job. If a migration has an ordering
   bug, a missing dependency, or assumes state a stale local DB happened to already have, this is where it
   would surface for the first time — and per the phase notebook's rule, that is an *application* defect
   needing a `P12.F<n>` fix slice, not something to patch inside this CI-wiring slice.
5. **`pnpm format:check` regressing between now and the first push** — low risk since `P12.S2` already
   swept the repo clean and this slice touches no `web/` source, but any file edited by a later slice
   between now and the actual push (S6 is ordered ahead of S4 per the operator's reordering) could
   reintroduce an unformatted file. Fix: run `pnpm format:check` (or `--write`) again immediately before
   the S4 push if any `web/` file was touched by an intervening slice.

## Deviations from `plan.md`

None in the landed `ci.yml`. One minor deviation in *how* validation step 1 was run: the plan's literal
`python3 -c "import yaml..."` invocation fails on this machine's bare interpreter (no system-wide PyYAML);
ran the identical check through `uv run python3` instead, which is strictly equivalent (same YAML parser,
same file, same assertion) and is noted above rather than silently substituted.
