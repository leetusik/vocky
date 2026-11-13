# Result — P12.S7: Author `docs/current/qa.md`

## Meta

**Status: done.** The doc convention this phase uses (see `phase.md` § "The doc convention this phase
uses") means the body below is **not** written to `docs/` — it is authored here, fenced under
"Proposed qa.md v0002 body", for `P12.REVIEW` to lift verbatim into `doc-new-version --doc qa`. No file
under `docs/` was touched. No code, test, or workflow-state change was made.

### Decisions

- Followed the plan's suggested shape almost exactly: philosophy → automated suites (Python + web
  topology and contracts) → local run commands → CI gates as they stand → smoke layers (unit,
  `vocky-smoke`, external smoke, the S4 production baseline) → manual checks automation cannot cover →
  honest `/qa-check` + `qa-agent` status. Added one short closing section ("What changes when you touch
  X") because the doc otherwise reads as a static snapshot with no guidance for the next contributor —
  matches the register of `operations.md`'s own short guidance asides.
- Every count in the body was **re-measured**, not copied from the plan's pre-researched numbers (see
  Validation below) — one correction found: the plan said "~225 test functions"; the actual, both by
  `pytest --collect-only` and by rerunning the suite, is **215** (215 passed, matching every prior slice's
  own measurement — S3 and S6 both independently reported 215). The doc states 215, not "~225".
- Did not build the `/qa-check` driver, per `intent.md`'s explicit scope line reproduced in `phase.md`'s
  routing table ("document QA only — do NOT build the driver"). The doc says plainly that `/qa-check` is
  unusable today and names exactly what building the driver would require, without proposing to do it.
- Did not touch `docs/current/qa.md`, `docs/index.json`, or run `doc-new-version` — confirmed by
  `git status` before and after (see Validation #3).

## Validation

**1. Every command named in the doc body exists where the doc says.**

```
$ grep -n "^test:\|^compose-up:\|^compose-down:\|^migrate:\|^wait-ready:\|^smoke-run:\|^smoke:\|^check-skill-parity:\|^bootstrap:\|^verify:\|^external-smoke:\|^external-verify:\|^check-test-db:" Makefile
23:check-test-db:
28:test: check-test-db
31:compose-up:
34:compose-down:
37:compose-logs:
40:migrate:
43:wait-ready:
46:smoke-run:
49:smoke: wait-ready
52:check-skill-parity:
55:bootstrap: sync compose-up migrate wait-ready
57:verify: smoke test
59:require-external-base-url:
62:external-smoke: require-external-base-url
65:external-verify: require-external-base-url
```
All twelve Make targets named in the doc exist at those lines. `web/package.json` scripts (`lint`,
`typecheck`, `test`, `format:check`, `build`) confirmed present via `python3 -c "import
json;print(json.load(open('web/package.json'))['scripts'])"` — all five keys present, matching the doc.

**2. Every count re-measured (not copied):**

| Claim | Method | Result |
|---|---|---|
| Python test files | `ls tests/*.py \| wc -l` (30, minus `conftest.py`) | **29** — matches plan |
| Python test functions | `uv run pytest --collect-only -q` (against a live local Postgres) | **215 tests collected** — corrects the plan's "~225" |
| Full Python suite, real DB | `DATABASE_URL=...55432/vocky TEST_DATABASE_URL=...55432/vocky_test uv run pytest -q`, against the sandbox's already-running `vocky-postgres-1` (`postgres:17`, `127.0.0.1:55432`) | **215 passed, 0 failed, 0 errors** in 9.37s |
| `test_admin_api.py` count | `grep -c "^def test_\|^async def test_" tests/test_admin_api.py` | **17** — matches plan |
| `test_public_access.py` count | same grep | **6** |
| CLI test files | `ls tests/test_cli_*.py` | **5** (`auth`, `capture`, `feedback`, `foundation`, `projects`) — matches plan |
| MCP transport test files | `ls tests/test_mcp_transport.py` | **1** — matches plan |
| TRUNCATE table list (`conftest.py`) | read `configured_database` fixture | **9 tables**: `feedback_events, feedback_comments, feedback_attachments, users, tenants, tenant_members, projects, project_credentials, auth_tokens` — matches plan |
| Web test files | `find web -name "*.test.ts" -not -path "*/node_modules/*"` | **10** — matches plan |
| Web test cases | `cd web && pnpm test` | **78 passed (78), 10 test files passed (10)** — matches plan |
| `ci.yml` jobs | read `.github/workflows/ci.yml` | **4**: `skill-parity`, `installer-syntax`, `web` (incl. `Format check` step), `pytest` — matches S6's landed result |
| `ci.yml` pytest job env contract | read the file | `DATABASE_URL`/`TEST_DATABASE_URL` both `...@localhost:5432/...`, `postgres:17` service, `pg_isready`/`10s`/`5s`/`5` — matches plan and `P12.S6/result.md` |
| `astral-sh/setup-uv` pin | read the file | `@v7` (the plan's `@v9` note was already corrected by the orchestrator before commit per `phase.md`'s "Orchestrator correction to P12.S6" — doc uses the landed `@v7`, not the stale `@v9`) |
| First CI runner run | `phase.md` § *P12.S4 complete* | green, run `30873072664`, push `6c16ac5`, 53s |
| `pnpm format:check` | `cd web && pnpm format:check` | clean, 0 files — matches `P12.S2`'s sweep holding |
| `deploy/backup.sh` / `status.sh` / `restore.md` exist | `ls deploy/` | all three present, plus `vocky.conf.md`, `deploy.sh`, `rollback.sh`, the two GH-Actions transport scripts |
| `deploy/restore.md` "never rehearsed" | read the file | line 3: *"Status: documented, never rehearsed."* — matches plan and doc |
| `VOCKY_AUTH_RATE_LIMIT`/`VOCKY_AUTH_RATE_WINDOW_S` | `grep .env.example` | present, commented, defaults `20`/`900` |
| `/qa-check` driver absent | `ls .claude/agents/`, `ls scripts/` | `qa-agent.md` (policy) + `.claude/skills/qa-check/` (contract) exist; **no** `scripts/qa-agent/`, no mission library — confirms the gap |

**3. `docs/current/qa.md` is still the untouched v0001 placeholder.**

```
$ git status --porcelain docs/ | head
(empty)
$ git diff --stat docs/current/qa.md docs/index.json
(empty)
```
No output from either — nothing under `docs/` changed. `docs/current/qa.md` still reads `version: v0001`,
`source: bootstrap`.

All validation commands were run in this sandbox against the local `vocky-postgres-1` container already
running there (not the production box — no ssh, no box contact, per the plan's boundary).

## Deviations from `plan.md`

One correction, not a scope deviation: the plan's pre-researched "~225 test functions" is superseded by
the measured **215** (both `pytest --collect-only` and a full green run agree, and it matches what `S3`
and `S6` each independently measured earlier in this phase) — the plan itself flagged this figure as
"spot-check, don't re-derive from scratch" for the cluster descriptions, but the count itself needed a
real re-measurement, which is what step 2 above is. No other deviation.

## Doc impact

- One line appended to `phase.md` § *Doc impact*, pointing `P12.REVIEW` at this file for the qa v0002
  body (per the phase's documented exception for `qa.md`).

---

## Proposed qa.md v0002 body

# Qa

## Status

This doc replaces the bootstrap placeholder with vocky's real QA picture as of **P12**: how the two
automated suites are shaped and run, the CI gates as they now stand (`P12.S6`, proven green on a real
runner at `P12.S4`), the smoke layers from a unit test up through the production bring-up baseline, the
manual checks automation cannot cover, and the honest, currently-unusable status of `/qa-check` +
`qa-agent`.

## Philosophy

This repo keeps test files **small and terse by default** — minimal high-value cases, no fixture or
scaffolding sprawl, lightweight verification (run the code, `make verify`, a smoke pass) preferred over
building out a suite for its own sake. A suite grows only on operator request or when the risk clearly
warrants it. Read the counts below as a snapshot of what earned a test, not a coverage target to chase.

## The Python suite (`tests/`)

**29 test files** (`test_*.py`) plus a shared `conftest.py`, flat directory, **215 test functions**
(`uv run pytest --collect-only`; confirmed by a full green run — see below). Roughly clustered by what
they exercise, inferred from filenames rather than a formal taxonomy:

- **Capture / ingest**: `test_capture_api`, `test_capture_queue`, `test_capture_validation`,
  `test_query_validation`
- **Worker / persistence**: `test_worker`, `test_persistence`, `test_storage`
- **Accounts / auth**: `test_accounts_persistence`, `test_accounts_provisioning`, `test_auth_api`,
  `test_cli_auth`, `test_credentials_api`, `test_org_credentials_api`, `test_org_credential_scope` — signup
  / login, tenant + org key minting, cross-tenant scoping
- **Read / manage APIs**: `test_app_api`, `test_app_feedback_api`, `test_project_feedback_api`,
  `test_user_feedback_api`, `test_usage_api`, `test_feedback_comments`, `test_public_access` (6 cases),
  `test_admin_api` (17 cases — the largest single file, the `/admin/api/*` bearer-guarded surface)
- **Attachments / storage**: `test_attachments_api`, `test_feedback_attachments`
- **CLI** (5 files): `test_cli_auth`, `test_cli_capture`, `test_cli_feedback`, `test_cli_foundation`,
  `test_cli_projects`
- **MCP transport** (1 file): `test_mcp_transport`

### The `conftest.py` contract — read this before running the suite anywhere

- Needs a **live Postgres**. `DATABASE_URL` (default
  `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky`) is the base connection; `TEST_DATABASE_URL`
  must resolve to a **different** database — the fixture raises `RuntimeError` if the two render equal or
  if `TEST_DATABASE_URL` has no database name.
- The session-scoped `test_database_url` fixture **creates the test database if it doesn't exist**, drops
  and recreates its `public` schema, and runs `alembic upgrade head` against it via a relative
  `alembic.ini` — the suite must run from the **repo root**.
- Every test using `configured_database` gets a `TRUNCATE` of **9 tables**
  (`feedback_events, feedback_comments, feedback_attachments, users, tenants, tenant_members, projects,
  project_credentials, auth_tokens`) before and after, so tests don't leak state across each other.
- An **autouse** fixture resets the in-process `/auth/*` rate limiter (`vocky.rate_limit`, `P12.S3`)
  before and after every test — without it, every test sharing `httpx.ASGITransport`'s fixed peer address
  across `/auth/signup`/`/auth/login` would eventually trip the limiter.
- **No Redis is needed** — `fakeredis` covers it as a dev dependency; confirmed empirically (0
  Redis-related failures locally), not just assumed.

## The web suite (`web/tests/`)

**10 `*.test.ts` files, 78 test cases**, run with **vitest** in the Node environment (no jsdom).
`vitest.config.ts` aliases `stubs/server-only.ts` so files importing Next's `"server-only"` guard can be
unit-tested outside a Next runtime. Rough clusters: app routes/shell (`vocky-app`, `agent-quickstart-ssr`,
`skill-preview-ssr`, `snippet-ssr`, `landing-copy`), auth routes (`auth-routes`, `vocky-auth`), session
crypto + guards (`session`, `session-guards`), and `clipboard`.

## Running everything locally

```sh
# Python suite — needs the two-database contract above
make test              # guards DATABASE_URL/TEST_DATABASE_URL, then `uv run pytest`

# Backend smoke against a running local stack
make smoke             # wait-ready + `uv run vocky-smoke`

# Both, in sequence
make verify             # smoke, then test

# Against a real external base URL (Cloudflare Tunnel / any HTTPS reverse proxy)
make external-smoke     # requires VOCKY_EXTERNAL_BASE_URL
make external-verify    # wait-ready + smoke-run against VOCKY_EXTERNAL_BASE_URL

# Skill-parity gate (the served/canonical SKILL.md byte check)
make check-skill-parity

# Web — from web/
pnpm lint
pnpm typecheck
pnpm test
pnpm format:check
pnpm build
```

`make test`'s `check-test-db` precondition fails loudly (not silently) if either DB var is unset or the
two are equal — copy `.env.example` to `.env` first if you haven't.

## CI gates as they stand (`.github/workflows/ci.yml`, extended by `P12.S6`)

Four jobs, on `push` to `main` and every `pull_request`:

| Job | What it checks |
|---|---|
| **Skill Parity** | `python3 scripts/skill_parity.py` — the served/canonical `SKILL.md` byte gate |
| **Installer Syntax** | `bash -n web/public/install.sh` |
| **Web** | `pnpm install --frozen-lockfile`, then `lint`, `typecheck`, `test`, and (new in P12) **`format:check`** — no exclusion left here |
| **Python Tests (Postgres)** *(new in P12)* | a `postgres:17` service container, health-gated on `pg_isready`; `DATABASE_URL`/`TEST_DATABASE_URL` both point at `localhost:5432` (not this workspace's local `55432` publish port — a GitHub-hosted service container maps differently); `uv sync --frozen` (via `astral-sh/setup-uv@v7`) then `uv run --no-sync pytest`; `timeout-minutes: 20` |

**This gate has actually run**, not just been authored: its first-ever runner execution (push `6c16ac5`,
run `30873072664`, triggered by `P12.S4`'s production push) went **green in 53 seconds**, with zero
iteration needed on either the new pytest job or the format-check step. A QA doc that documents a gate
that has never executed is weaker than one that documents a proven one — this one is proven.

No Python lint/`ruff` step runs in CI; `ruff check` is clean as of the last slice that touched Python code
but is not gated.

## Smoke layers

1. **Unit/integration** — the 215-test Python suite and 78-test web suite above, run on every push/PR.
2. **`vocky-smoke`** (`vocky.smoke:main`, `src/vocky/smoke.py` — httpx + stdlib only, no test framework):
   hits `GET /healthz`, then walks the real account control plane — signup, create a project, mint a
   per-project `vk_` ingest key — then `POST /api/feedback` with that key, and polls the scoped
   `GET /api/feedback` (up to 20×0.5s) until the worker-persisted record appears, asserting the captured
   context (`user_id`, `target_type`, `target_id`, `target_role`, `target_text`) round-tripped. `make
   smoke` runs it against a local stack; `make external-smoke` / `external-verify` run the same check
   against `VOCKY_EXTERNAL_BASE_URL`.
3. **The `P12.S4` production bring-up baseline** — the manual-QA reference for `vocky.hi2vi.com`, executed
   once, live, on 2026-08-04:
   - `GET /healthz` and `GET /` both 200.
   - **Signup → session round-trip**: `POST /api/auth/signup` → 200, httpOnly `vocky_session` cookie set,
     authenticated `GET /dashboard` → 200 (anonymous → 307 to `/login`). **BFF origin-gate trap**:
     origin-less non-browser POSTs to `/api/auth/*` get **403 by design** (`session.ts`'s CSRF layer) — a
     real browser always sends `Origin`/`Sec-Fetch-Site`, so this is expected, not a bug. When curling
     this surface for QA, send `Origin: https://vocky.hi2vi.com` explicitly.
   - `/install.sh` and `/SKILL.md` both 200, served `SKILL.md` **byte-identical** (`cmp` clean) to
     `skills/vocky-feedback/SKILL.md`.
   - Clean-container `curl | bash` install: `buildpack-deps:bookworm-scm`, uv bootstrapped, `vocky 0.2.0`
     from `git+https://github.com/leetusik/vocky@<sha>`, `vocky --version` and `vocky capture --help`
     both render.
   - **Cloudflare is not a barrier**: proven three ways (script-served shell, non-browser JSON POST, `uv`
     git fetch) — no challenge interfered with any of them.
   - All co-tenant vhosts on the shared edge (`hi2vi.com`, `knowledge.hi2vi.com`, `changple.ai`,
     `miracle.changple.ai`) verified still 200 after the vocky vhost reload.

   Full evidence: `works/phases/active/P12/slices/P12.S4/result.md` (or its archived location once P12
   archives).

## Manual checks automation cannot cover

- **The BFF origin-gate trap above** — every future manual/QA probe against `/api/auth/*` needs a real
  `Origin` header or it will read as a false failure.
- **The restore drill** (`deploy/restore.md`, authored `P12.S5`) is **documented but never rehearsed**.
  It covers: verify a `.sql.gz` dump in a scratch database before touching anything live, the real
  database cutover (stop `api`/`worker`, drop/recreate, restore, `alembic upgrade head` sanity check,
  bring the stack back up and re-gate), and the attachments-volume cutover — independent of the database
  restore. Its own header says plainly: *"Treat this file as a starting draft to be corrected by that
  first real run, not as a proven procedure."* The first real rehearsal is an operator action, ideally on
  a quiet window rather than during an incident.
- **Backup/rotation is authored, applied once, unrehearsed for restore**: `deploy/backup.sh` (nightly
  `pg_dump` + gzip, an alpine-throwaway-container tar of the attachments volume, 14-day retention on
  both, Redis deliberately skipped) and `deploy/status.sh` (read-only `compose ps` + health + disk +
  volume sizes + recent log lines — explicitly basic, not monitoring infra).
- **Rate-limit interaction with a manual stress pass**: the in-process `/auth/signup` + `/auth/login`
  limiter (`vocky.rate_limit`, `P12.S3`) defaults to 20 requests / 15 minutes per `(IP, route)`. A
  scripted or manual QA pass that retries either route more than that from one source will legitimately
  hit `429` — space retries, or set `VOCKY_AUTH_RATE_LIMIT=0` in the box `.env` for a deliberate stress
  pass and restore it after.
- **Visual/design sign-off**: nothing in P12 touches product visual design (`P12.S2`'s token rename was a
  byte-identical-hex mechanical edit, verified by grep, not a visual change) — there is no design gate to
  cover here as of this doc's version.

## `/qa-check` + `qa-agent` — honest status

The workspace ships the **policy** (`.claude/agents/qa-agent.md` — a read-only agent that drives a
project-supplied browser/UI driver turn-by-turn like a curious human tester, expecting verbs like
`observe`, `click`, `network_tail`, `mutation_window`) and the **contract**
(`.claude/skills/qa-check/SKILL.md`, `disable-model-invocation: true` — explicit-invocation only). **The
repo has no driver.** There is no `scripts/qa-agent/`, no mission library, no artifact pipeline, and no
browser runtime wired to it. Until a driver exists, **`/qa-check` is non-functional in this repo** — the
command exists, the agent it dispatches to exists, but there is nothing underneath for either to drive.

Wiring it would require, at minimum: a project-specific driver process exposing the verb set
`qa-agent.md` assumes (`observe`, `screenshot`, `click`, `type`, `keyboard`, `wait_for_selector`,
`wait_for_ms`, `goto`, `console_tail`, `network_tail`, `inspect_dom`, `mutation_window`, `stop`) against
a real browser session, a mission-brief library under a project-defined path, and an artifact-directory
convention for `transcript.md`/`summary.json`. Building that is a feature-scale addition, not a
hardening pass, and is out of scope for P12.
