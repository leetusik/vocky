# Plan — P12.S7: Author `docs/current/qa.md` (as v0002 content, delivered via result.md)

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-mid` (risk `medium`).

## The doc convention — where the body goes

**You author the complete QA doc body into this slice's `result.md`, NOT into `docs/`.** Durable docs
are versioned once per phase at the review slice: `P12.REVIEW` will run
`doc-new-version --doc qa --summary … --source P12.REVIEW` and paste your body in as **v0002** — the
first real content this doc has ever had (it is still the ~11-line `v0001_bootstrap` placeholder).
Never run `doc-new-version` yourself; never hand-edit `docs/current/qa.md` or `docs/index.json`.

Structure `result.md` as: a short meta section (decisions, verification, notes for REVIEW), then a
clearly delimited `## Proposed qa.md v0002 body` section containing the full doc verbatim, ready to
lift. Match the voice and density of the other `docs/current/*.md` docs (read one — `operations.md` or
`backend.md` — for register; frontmatter is added by the engine, do not write it).

## Grounded facts (pre-researched — spot-check, don't re-derive from scratch)

A read-only scout swept the tree on 2026-08-04. Verify by sampling, then trust:

- **Python suite** (`tests/`): 29 test files + `conftest.py`, ~225 test functions, flat dir. Clusters:
  capture/ingest (`test_capture_*`, `test_query_validation`), worker/persistence, accounts/auth
  (signup/login, tenants, `vk_` key minting, cross-tenant scoping), read/manage APIs (incl.
  `test_admin_api.py` 17 tests, `test_public_access.py`), attachments/storage, CLI (5 files), MCP
  transport (1). Cluster descriptions were filename-inferred — **spot-check two or three bodies**
  before asserting coverage claims in the doc.
- **conftest contract**: live Postgres; `DATABASE_URL` (fallback `…127.0.0.1:55432/vocky`) +
  `TEST_DATABASE_URL` which must render a *different* database (RuntimeError otherwise); creates the
  test DB, drops/recreates `public`, runs `alembic upgrade head` via relative `alembic.ini` (repo root
  required); per-test TRUNCATE of 9 tables + autouse rate-limiter reset; no Redis needed (fakeredis).
- **Web suite** (`web/tests/`): 10 `*.test.ts`, 78 cases, Node env (no jsdom), vitest;
  `stubs/server-only.ts` aliased in `vitest.config.ts`. Clusters: app routes/shell, auth routes,
  session crypto + guards, SSR/copy checks, clipboard.
- **Local commands**: `make test` (guards the two-DB rule, then `uv run pytest`); `make smoke`
  (= wait-ready + `uv run vocky-smoke`); `make verify` = smoke + test; `make external-smoke` /
  `external-verify` (need `VOCKY_EXTERNAL_BASE_URL`); web from `web/`: `pnpm lint`, `typecheck`,
  `test`, `format:check`, `build`; `make check-skill-parity`.
- **`vocky-smoke`** = `vocky.smoke:main` (`src/vocky/smoke.py`, httpx + stdlib only): `/healthz` →
  provision `vk_` key → `POST /api/feedback` → poll scoped `GET /api/feedback` until the
  worker-persisted record appears.
- **CI (`.github/workflows/ci.yml`)**, four jobs after S6: skill-parity, installer-syntax, web
  (lint/typecheck/vitest/format:check), pytest (`postgres:17` service container, both DB URLs in job
  env, repo-root, `uv sync --frozen` → `uv run --no-sync pytest`). **Its first-ever runner execution
  (push `6c16ac5`, run 30873072664) was green in 53s** — say so; a QA doc that documents a gate that
  has never run would be weaker than one that documents a proven gate. No Python lint/ruff step in CI.
- **Production smoke evidence (this phase, S4)**: the full bring-up smoke that now constitutes the
  manual-QA baseline — `/healthz` + `/` 200, signup→session round-trip (note the BFF origin-gate trap:
  origin-less curl POSTs 403 by design — document it, QA runs hit it), `/install.sh` + `/SKILL.md`
  200 + byte parity, clean-container `curl | bash` install, Cloudflare-not-a-barrier, co-tenant
  checks. See `phase.md` § *P12.S4 complete* and S4's `result.md`.
- **`/qa-check` + `qa-agent`: unwired, and the doc must say so honestly.** The workspace ships only
  the policy (`.claude/agents/qa-agent.md` — assumes a project driver exposing `observe`, `click`,
  `network_tail`, etc.) and the contract (`.claude/skills/qa-check/SKILL.md`,
  `disable-model-invocation: true`). The repo has **no driver**: no `scripts/qa-agent/`, no mission
  library, no artifact pipeline. Until a driver exists, `/qa-check` is non-functional here. (A
  deferred job for defining that driver will be opened by the orchestrator — mention the gap, not the
  job number.)
- **Restore drill**: `deploy/restore.md` exists as of S5 and has **never been rehearsed** — that
  unrehearsed status is a QA fact worth recording.
- **Governing philosophy** (CLAUDE.md hard rule): test files stay small/terse; lightweight
  verification preferred; suites grow only on operator request or clear risk. The doc should state
  this as policy, not apologize for it.

## Shape of the doc (guidance, not a straitjacket)

Roughly: what QA means here (philosophy) → the automated suites (Python topology + contract, web
topology) → how to run everything locally (exact commands) → the CI gates as they stand (proven
green) → smoke layers (`vocky-smoke`, external smoke, the S4 production bring-up baseline) → manual
checks automation cannot cover (auth round-trip nuances, restore drill, visual/design sign-off if
relevant) → `/qa-check` + `qa-agent` honest status and what wiring them would require. Keep it tight —
this repo's docs are dense, not long.

## Boundaries

- Write only: this slice's `result.md`, and appends to `phase.md`. **No other file.**
- No code changes, no test changes, no `docs/` edits, no `doc-new-version`, no commits, no workflow
  state commands, no ssh, no box contact.

## Validation

1. Every command named in the doc body exists where the doc says (grep Makefile / package.json).
2. Every count (files, tests, jobs) re-measured, not copied — report the measured numbers.
3. Confirm `docs/current/qa.md` is still the untouched v0001 placeholder (you change nothing there).

## Deliverables

- `result.md` per the convention above (meta + full v0002 body).
- `phase.md` § *Findings & Notes*: two or three lines — the doc is authored and staged for REVIEW,
  and the `/qa-check` driver gap.
- `phase.md` § *Doc impact*: one line telling `P12.REVIEW` to consolidate the body as qa v0002 with
  `--source P12.REVIEW`.
