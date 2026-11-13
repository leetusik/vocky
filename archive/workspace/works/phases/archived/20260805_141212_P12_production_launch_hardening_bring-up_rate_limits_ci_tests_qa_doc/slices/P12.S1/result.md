# Result — P12.S1: Decide the fate of `/admin/api/*` and `VOCKY_ADMIN_AUTH_TOKEN`

## Decision honored (not re-opened)

The operator's 2026-08-04 decision (`phase.md` § "Operator decisions", Open Question 2) stands: **KEEP
`/admin/api/*`, FAIL CLOSED.** Nothing was deleted — `src/vocky/admin_api.py`, its nine routes,
`tests/test_admin_api.py`, and `Settings.admin_auth_token` are all untouched. `VOCKY_ADMIN_AUTH_TOKEN`
remains a required production box secret and stays on `P12.S4`'s operator-gate list.

If I had to weigh in: the decision is sound. The nine routes are a real, working review surface with no
first-party client removal risk, and fail-closed + a `:?` compose gate closes the actual defect (fail-open
on a blank token) at essentially zero cost. I see no reason to revisit "retire" later unless an operator
surfaces an actual admin client need.

## What changed

### 1. `src/vocky/auth.py` — `AdminBearerAuthMiddleware` fails closed

Restructured `__call__` (was a single flattened `if self.token and ... and not is_authorized_bearer(...)`)
into two nested checks on `is_admin_api_path(...)` (reused, no new path test written):

- **No token configured** (`self.token` empty after `.strip()`, unchanged from `__init__`) → **`503`**,
  body `{"detail": "Admin API is not configured"}`, **no** `WWW-Authenticate` header. Chosen per the plan:
  `503` signals server misconfiguration, is unambiguous in logs, and does not invite a credential retry
  (`401` + `WWW-Authenticate` would).
- **Token configured** → unchanged behaviour: `is_authorized_bearer(...)` or `401` +
  `WWW-Authenticate: Bearer`.
- Non-admin paths fall through untouched on both branches (the outer `if` is scoped to
  `is_admin_api_path`, exactly as before).
- Docstring rewritten — no longer says "when a token is configured".

### 2. `compose.prod.yml` — all three production secrets fail loudly

- `VOCKY_ADMIN_AUTH_TOKEN` (api service, was a plain `${VOCKY_ADMIN_AUTH_TOKEN}`) → now
  `${VOCKY_ADMIN_AUTH_TOKEN:?VOCKY_ADMIN_AUTH_TOKEN is required — set it in the box .env}`, plus a comment
  explaining why (the middleware's fail-closed `503` alone isn't enough — Compose itself must refuse to
  start with a blank secret).
- **Deliberate scope extension, per the plan** (`phase.md` Finding 2): gave `POSTGRES_PASSWORD` and
  `SESSION_SECRET` the same `:?` treatment **everywhere they're interpolated in the file** — that's 3
  occurrences of `POSTGRES_PASSWORD` (the `postgres` service's own env var, and the `DATABASE_URL` string
  built into both `api` and `worker`) and 1 of `SESSION_SECRET` (`web`). `POSTGRES_PASSWORD` previously
  failed only by the `postgres:17` image's own refusal to init blank, not by Compose; `SESSION_SECRET`
  previously failed only at a user's first login (long after the health gate is green, since the web
  healthcheck fetches `/`, which never reads it). Both are now Compose-level failures, matching
  `operations.md`'s "must fail loudly" claim for the first time.
- Reconciled the file's own header comment (top) and the web-service `SESSION_SECRET` comment to describe
  the `:?` form and its consequence.
- Left the `compose.prod.yml:100-103` comment about the removed Admin Web UI, and the `docker compose exec
  vocky-api …` idiom comment near the api service, exactly as instructed / out of scope.

### 3. `.env.prod.example` — marked all three secrets required

Values stay empty (still a template). Header + each of the three per-secret comments now say plainly that
the value is **required** and that Compose aborts on a missing one, instead of implying it's optional. Kept
the `openssl rand -base64 32` generation guidance. Left `.env.example` (dev) and `docker-compose.yml`
untouched, as instructed — dev's default stays "no token", now meaning local `/admin/api/*` returns `503`
until the operator sets one; that consequence is now documented at `README.md:210`/`:222`, not
special-cased in code.

### 4. `tests/test_public_access.py` — both middleware branches covered

Kept `test_admin_bearer_auth_middleware_requires_configured_token` (the configured-token case) byte-for-byte
unchanged. Added one new test, `test_admin_bearer_auth_middleware_fails_closed_without_a_configured_token`,
following the file's existing bare-`Starlette` + `TestClient` style:

- No token configured → `/admin/api/healthz` and `/admin/api/feedback/metrics` both `503` with
  `{"detail": "Admin API is not configured"}`, and **no** `www-authenticate` header on either response.
- On that same unconfigured app, `/healthz` (a non-admin route) still passes through `200`.

Terse by design — 2 new assertions blocks in one test function, no new fixtures.

### 5. `README.md` — the admin story matches the fail-closed model

Nine `VOCKY_ADMIN_AUTH_TOKEN` mentions total (was also nine before). Edited the stale ones:

- `:34` — rewrote the "packaged Admin Web UI … scheduled for removal in P6" line (P6 already shipped that
  removal) into a statement that it's gone and Admin REST now fails closed.
- `:210` — dropped the "Admin UI token field" instruction (no UI exists); replaced with "check with
  curl/an HTTP client … `503` until configured".
- `:222` — "when set" → "required … mandatory to expose Admin REST at all … `503` … fails closed."
- `:258`/`:259` — merged the two admin bullets into one; dropped the dead "packaged (superseded, P6-removal)
  Admin Web UI under `/admin`" bullet entirely (nothing lives there any more).
- `:273` (plan's "~274") — "set `VOCKY_ADMIN_AUTH_TOKEN` before exposing" → "(required — answers `503`
  until it is set, it is never openly reachable)".
- `:444` (plan's "~445") — "Set … before exposing … outside a trusted environment" (implying it's optional
  inside a trusted one) → "is **required** … fails closed … the surface is never openly reachable."
- Left `:32` and `:430` as the plan said (already correct), and left `:336` (`"...when /admin/api/* is
  exposed"`, about public vs. local reachability, not about token optionality — still accurate) untouched;
  it wasn't in the plan's enumerated line list and doesn't misstate the fail-closed model.

## Validation (all four plan steps run)

1. **`uv run pytest tests/test_public_access.py tests/test_admin_api.py`** → **23 passed** (6 in
   `test_public_access.py` including the new test, 17 in `test_admin_api.py`, unaffected as predicted since
   that file builds a bare `Starlette` app with no middleware).

2. **Lint.** `ruff` is not installed as a bare binary in this sandbox (`ruff: command not found`); ran it via
   `uv run --with ruff ruff ...` instead. No `lint` target exists in the `Makefile` (`grep lint Makefile` is
   empty) — confirmed rather than invented one, per the plan's fallback instruction.
   - `ruff check src/vocky/auth.py tests/test_public_access.py` → **all checks passed**.
   - `ruff format --check src/vocky/auth.py tests/test_public_access.py` → reports 2 files "would be
     reformatted" (a wrapped `dict(...).get(...).decode(...)` chain in `auth.py`, and a wrapped `assert`/
     `async with` line in `test_public_access.py`). **Confirmed pre-existing, not introduced by this
     slice**: stashed the working tree and re-ran the same command against `main`'s versions of both
     files — the identical two format complaints appear at the pre-edit line numbers (97/204 in the old
     `auth.py`, 25/113 in the old `test_public_access.py`). This slice's new lines (the `503` branch, the
     new test) are not among the reported spans; the repo already carries this format debt for reasons
     unrelated to P12.S1 and it is out of this slice's scope to fix.
   - `uv run ruff check src tests` (whole tree, informational) does report 35 pre-existing errors, none in
     the two files this slice touched — a pre-existing lint backlog outside this slice's scope.

3. **Compose.** Docker Desktop + `docker compose` v2.37.1 are available in this sandbox (contrary to
   `phase.md`'s Finding that neither is installed — that note was about `shellcheck`/`actionlint` and a
   *running* Docker daemon for `up`, and turned out to also not apply to the CLI itself). Ran `config -q`
   with `--env-file` pointed at an empty scratch file to exclude the repo's real dev `.env` (which already
   carries all three secrets and would have silently masked the test):
   - All three secrets exported as dummy values → `docker compose --env-file <empty> -f compose.prod.yml
     config -q` → **exit 0** (succeeds).
   - `VOCKY_ADMIN_AUTH_TOKEN` unset (only `POSTGRES_PASSWORD`/`SESSION_SECRET` exported) → **exit 1**,
     `error while interpolating services.api.environment.VOCKY_ADMIN_AUTH_TOKEN: required variable
     VOCKY_ADMIN_AUTH_TOKEN is missing a value: VOCKY_ADMIN_AUTH_TOKEN is required — set it in the box
     .env`.
   - Also verified (beyond the plan's minimum) that `POSTGRES_PASSWORD` unset and `SESSION_SECRET` unset
     each independently fail the same way, proving the scope-extension edit actually works for all three,
     not just the one the plan named explicitly.

4. **`grep -rn "VOCKY_ADMIN_AUTH_TOKEN" README.md`** → 9 matches, all now describe the fail-closed model
   (listed above under "What changed" § 5); output reproduced in this file's validation section above.

`python3 scripts/workflow.py validate` also run (state-integrity check) → `Workflow validation passed.`

## Deviations from `plan.md`

None in scope or approach. Two things worth flagging, both already anticipated by the plan's own fallback
language:
- Lint: no repo `Makefile` lint target exists, so I ran the plan's literal `ruff check`/`ruff format
  --check` commands via `uv run --with ruff` since bare `ruff` isn't on PATH here — same commands, just
  invoked through `uv run --with` instead of a bare binary.
- Compose: the CLI was present (plan anticipated it might not be, with a documented Python/yaml fallback);
  used the real `docker compose config -q` path as the plan's primary instruction says, and additionally
  had to pass `--env-file <empty>` to defeat the repo's real dev `.env` auto-load, which is not itself a
  deviation from the plan's intent (the plan's test is "with the three secrets exported to dummy values" /
  "with `VOCKY_ADMIN_AUTH_TOKEN` unset" — both are satisfied exactly as specified, the `--env-file` flag
  was just the mechanism needed to make "unset" actually mean unset in this sandbox).

## What `P12.S4` (the bring-up) must now know

- `VOCKY_ADMIN_AUTH_TOKEN` is confirmed still on the box `.env` secret list — no change to S4's
  secret-generation gate.
- All **three** production secrets (`POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`) now
  abort `docker compose` (including `up`) if the box `.env` is missing any of them — S4's deploy will fail
  fast and loud at the compose step rather than starting with a degraded/insecure service, which is a
  strictly better failure mode for the first-ever bring-up.
- Local dev is unaffected in code: `docker-compose.yml` and `.env.example` were not touched. A local
  `/admin/api/*` call now returns `503` instead of the old "open by default" behaviour whenever
  `VOCKY_ADMIN_AUTH_TOKEN` isn't set in the dev `.env` — this is the documented, intended consequence
  (`README.md:210`/`:222`), not a regression.

## Doc impact appended to `phase.md`

See `phase.md` § "Doc impact" — added a P12.S1 line covering: `architecture.md`'s open question about
whether Admin REST outlives the UI it served is now resolved (kept, fail-closed, token mandatory);
`security.md`'s defense-in-depth claim about `/admin/api/*` is now actually true in code; and
`operations.md`'s "missing box secret fails loudly" claim is now true for all three secrets, superseding
the correction `P12.DECOMP` filed for that same claim.
