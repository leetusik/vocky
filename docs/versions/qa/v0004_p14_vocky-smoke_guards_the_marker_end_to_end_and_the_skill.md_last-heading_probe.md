---
doc_id: qa
version: v0004
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: vocky-smoke guards the marker end to end, and the SKILL.md last-heading probe
previous: v0003_p13_the_python_suite_is_30_files_and_225_tests_ruff_is_not_configured_in_this_repo_at_all_and_the_feedback_alert_has_a_two-part_live_verification
---

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

**30 test files** (`test_*.py`) plus a shared `conftest.py`, flat directory, **238 test functions**
(`uv run pytest --collect-only`, re-counted at P14.REVIEW; confirmed by a full green run — see below).
P14 added 13 cases and **no new file**, which is the repo's standing preference: extend the existing
capture/queue/persistence/query files rather than open a new one for each field.
Roughly clustered by what they exercise, inferred from filenames rather than a formal taxonomy:

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
- **Notifications** (P13, 1 file): `test_notifications` (5 cases, pure-Python, **no DB**) — the
  unconfigured-SMTP skip, the `record is None` / `project_id is None` skips, one full send against a
  monkeypatched `_send_message`, and the "no owner email" skip. The alert's *containment* is tested
  where it lives, in `test_worker` (`test_worker_notifies_after_persist`,
  `test_worker_contains_notifier_failure` — a raising notifier must leave both the queue and the
  dead-letter list empty).

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

**Two assertions in this repo mirror an artifact rather than a contract, and both bite predictably:**

- **`web/tests/skill-preview-ssr.test.ts` pins `SKILL.md`'s *last section heading*** as its "the whole
  file shipped, nothing was truncated" probe. **Any section added to or renumbered in the skill must
  update that one line** (P14 grew the skill from 7 numbered steps to 8 and had to). The neighbouring
  line/byte-count assertions are computed from the file at test time and never need touching.
- **`tests/test_admin_api.py::test_admin_list_feedback_preserves_legacy_channel_filter` compares the
  whole serialized record as an exact dict** — it is the only full-record exact-dict comparison across
  `tests/` and `web/tests/`. **Every new response field lands on exactly this one line.** Editing it is
  not an additivity violation: additivity is a client-contract property (the JSON gains one nullable key,
  nothing is renamed or retyped), and a serializer snapshot is a mirror of the serializer, not a client.
  The `null` the new key carries there is itself the additivity proof.

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

**There is no Python lint or type-check step anywhere in this repo — not in CI, not locally** (verified
independently by three P13 slices). `ruff` is not a dependency, there is no `[tool.ruff]` section in
`pyproject.toml`, there is no Makefile lint target, and the binary is not installed (`uv run ruff
--version` fails to spawn); `mypy` is likewise absent. Treat any plan step that says "run ruff if
configured" as a **no-op here**, and do not report a lint pass that never ran.

## Smoke layers

1. **Unit/integration** — the 238-test Python suite and 78-test web suite above, run on every push/PR.
2. **`vocky-smoke`** (`vocky.smoke:main`, `src/vocky/smoke.py` — httpx + stdlib only, no test framework):
   hits `GET /healthz`, then walks the real account control plane — signup, create a project, mint a
   per-project `vk_` ingest key — then `POST /api/feedback` with that key, and polls the scoped
   `GET /api/feedback` (up to 20×0.5s) until the worker-persisted record appears, asserting the captured
   context (`user_id`, `target_type`, `target_id`, `target_role`, `target_text`, and as of P14
   `recorded_by`) round-tripped. `make smoke` runs it against a local stack; `make external-smoke` /
   `external-verify` run the same check against `VOCKY_EXTERNAL_BASE_URL`.

   **The reference payload is the deploy-time guard against silent capture-field loss (P14).** The
   in-process suite covers a new capture field, but the Redis queue's hand-written
   `_serialize_payload`/`_deserialize_payload` pair is the one place a field is dropped **silently** —
   no error, the value simply never reaches the worker. `vocky-smoke` is the only check that exercises
   app → Redis → worker → Postgres → read against a **deployed** environment (`make smoke`,
   `external-smoke`, `external-verify`, and the deploy script's post-deploy gate), which is exactly where
   that failure hides. **Every future capture field should extend this same payload and assertion** —
   three lines inside the loop that already exists, not a new harness or file.
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

## Verifying feedback email alerts (P13)

**No automated layer covers the alert end to end** — the suite tests the notifier and the worker's
containment with fakes, and neither `vocky-smoke` nor CI ever opens an SMTP connection. Live
verification is manual and has two halves, both required (the full runbook, including the box-side
credential discovery, is in `operations.md`):

1. Capture one real feedback event against the target deployment. `VOCKY_EXTERNAL_BASE_URL=https://vocky.hi2vi.com make external-smoke`
   is the easiest full round trip, but note it **signs up a throwaway account** — the alert then goes to
   *that* account's owner, not to you. To see the mail yourself, capture into a project whose org you own.
2. Check both signals: `docker logs vocky-worker --since 5m` shows the job persisted with **no
   `Feedback alert failed` line** (that exact string is the worker's `logger.exception` message and the
   only in-band failure signal), **and** the plain-text mail actually arrives in the org owner's inbox.
   A clean log alone proves nothing about delivery — some providers accept the SMTP transaction and drop
   the message when the From identity is unauthorized.

**Baseline, executed live 2026-08-04 (P13.S5):** both halves passed against `vocky.hi2vi.com` using the
SMTP account changple5 already sends with (`mail.privateemail.com:587`, STARTTLS). Evidence:
`works/phases/active/P13/slices/P13.S5/result.md` plus the operator's acceptance note in that phase's
`phase.md`.

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
- **Feedback alert delivery** — see the P13 section above. Nothing automated ever sends real mail, and a
  silently-dropped message leaves no trace in vocky at all (a failed alert is logged and lost, by design).
- **Visual/design sign-off**: nothing in P12, P13, or P14 touches product visual design (`P12.S2`'s token rename was a
  byte-identical-hex mechanical edit, verified by grep, not a visual change; P14 deliberately added **no**
  rendered dashboard control for the new marker, only a URL-driven filter) — there is no design gate to
  cover here as of this doc's version.
- **Live MCP capture over the real transport.** Nothing in CI opens an MCP session: `tests/test_mcp_transport.py`
  is the suite's **single** caller of `mcp.session_manager.run()`, and `vocky-smoke` is REST-only. P14's
  end-to-end proof (a real authenticated `initialize` → `tools/list` → `tools/call` against a running
  container, read back from Postgres) was therefore a **manual** slice-time check, and any future change to
  the MCP tool schema or its transport needs the same manual pass. **Rebuild the images first** — `make
  compose-up` passes `--build`, and a running container can easily predate the code under test, in which
  case a "live" result proves nothing. When probing `/mcp` with a spoofed `Host`, hit **`/mcp/` directly with
  redirects off**: the `307` to `/mcp/` is built from the spoofed `Host`, so following it sends the request
  off-box (P14 hit the real public deployment this way and read the resulting `401` as a local failure).

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
