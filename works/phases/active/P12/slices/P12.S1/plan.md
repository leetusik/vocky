# Plan — P12.S1: Decide the fate of `/admin/api/*` and `VOCKY_ADMIN_AUTH_TOKEN`

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-mid` (risk `medium` — bounded, no module removal).

## The decision is already made — do not re-open it

The operator settled `phase.md` Open Question 2 on 2026-08-04, before this slice was planned:

> **KEEP the `/admin/api/*` surface, but make it FAIL CLOSED.**

So: **nothing is deleted.** `src/vocky/admin_api.py`, its nine routes, `tests/test_admin_api.py` and the
config field all stay. `VOCKY_ADMIN_AUTH_TOKEN` **remains a required production box secret** and stays on
`P12.S4`'s operator-gate list. Your job is to close the fail-open hole and make the truth-of-record match.

Do **not** delete the admin API, do not add a new enable/disable feature flag, and do not redesign the
auth model. If you believe the decision is wrong, say so in `result.md` — do not act on it.

## Why this slice is first (the defect it closes)

`src/vocky/auth.py:92-99` — `AdminBearerAuthMiddleware.__call__` guards `/admin/api/*` **only
`if self.token`**. `src/vocky/config.py:39` defaults `VOCKY_ADMIN_AUTH_TOKEN` to `""`.
`compose.prod.yml:104` interpolates a plain `${VOCKY_ADMIN_AUTH_TOKEN}` — for an unset variable Compose
substitutes an **empty string with a warning**, it does not fail. Net effect: one missing or typo'd `.env`
line ships **nine unauthenticated `/admin/api/*` routes**, including `PATCH` and `DELETE` on any feedback
record, reachable by every co-tenant container on `changple_shared_network`. The edge `return 404` on
`/admin/` keeps it off the public internet, but the "defense in depth" claim in `security.md` /
`operations.md` currently rests on a token that is optional in code.

This must not survive the bring-up (`P12.S4`), which is why the slice is ordered first.

## Changes

### 1. `src/vocky/auth.py` — the middleware fails closed

Drop the `self.token and` short-circuit from the `if` in `AdminBearerAuthMiddleware.__call__` and split
the behaviour in two, for `scope["type"] == "http"` requests whose path satisfies the existing
`is_admin_api_path()` helper (reuse it — do not write a new path test):

- **No token configured** (`self.token` empty after `.strip()`) → refuse every admin request with
  **`503`** and body `{"detail": "Admin API is not configured"}`. `503` (not `401`, not `404`) because
  this is a server misconfiguration, not a client credential problem: it must be unmistakable in the box
  logs and must never invite a retry with credentials. Do **not** send `WWW-Authenticate` on this branch.
- **Token configured** → the existing behaviour, unchanged: `is_authorized_bearer(...)` or `401` +
  `WWW-Authenticate: Bearer`.

Update the class docstring — it currently says "when a token is configured", which is exactly the
behaviour being removed. Reuse the existing `JSONResponse` construction idiom already in the method.
Non-admin paths must be untouched on both branches.

### 2. `compose.prod.yml` — a missing secret fails the deploy loudly

- Line ~104: `VOCKY_ADMIN_AUTH_TOKEN: ${VOCKY_ADMIN_AUTH_TOKEN:?...}` with a short, actionable error
  message naming the box `.env`.
- **Deliberate scope extension (do this too):** give `POSTGRES_PASSWORD` and `SESSION_SECRET` the same
  `${VAR:?...}` treatment wherever they are interpolated in this file. Rationale: `phase.md` Finding 2
  records that `operations.md`'s claim *"a missing value must fail loudly on the box"* is **false as
  written** for all three; `POSTGRES_PASSWORD` only fails by the `postgres:17` image's grace and
  `SESSION_SECRET` fails at first login, long after the health gate is green. These are one-line edits of
  the same kind, they make the documented claim true, and they de-risk `P12.S4`. Nothing else in the file
  changes.
- Reconcile the file's own header comment (~line 23) and the web-service comment (~line 195) with the new
  interpolation form if they describe it.
- Note for the executor: `compose.prod.yml:100-103` already carries a correct comment saying the packaged
  Admin Web UI was removed in P6.S1 — leave it.

### 3. `.env.prod.example` — mark the three secrets as required

Line ~21 `VOCKY_ADMIN_AUTH_TOKEN=` and its neighbours: keep the values empty (this file is a template, not
a secret store), but make the comments state plainly that these are **required** and that a missing value
now aborts `docker compose` rather than silently degrading. Keep the existing `openssl rand -base64 32`
generation guidance if present.

The dev-side `.env.example:21` and `docker-compose.yml` stay as they are — the dev default remains "no
token", which now means local `/admin/api/*` returns `503` until the operator sets one. That is the
intended consequence; document it (below), do not special-case dev in code.

### 4. Tests — prove both branches

`tests/test_admin_api.py` builds its own bare `Starlette(routes=admin_routes)` with **no middleware**, so
its 17 tests are unaffected. The middleware's tests live in `tests/test_public_access.py` (it already
imports `AdminBearerAuthMiddleware` and `is_admin_api_path`, and constructs an app with
`token="secret"` at ~line 63). Extend **that** file, following its existing style:

- **New:** an app built with `AdminBearerAuthMiddleware` and **no token** → `/admin/api/healthz` and
  `/admin/api/feedback/metrics` return `503`, and the body carries the `detail` string; assert **no**
  `WWW-Authenticate` header on this response.
- **New:** on that same unconfigured app, a non-admin route still passes through untouched.
- **Keep** the configured-token cases exactly as they are (missing bearer → `401` + `WWW-Authenticate`,
  correct bearer → through).

Keep the additions terse — a couple of high-value cases, no fixture sprawl (`AGENTS.md`).

### 5. `README.md` — make the admin story true

Three lines are stale (P6.S1 deleted the packaged Admin Web UI; there is no `/admin` app any more, and the
edge 404s the whole prefix), plus three that describe the old "guarded when set" model:

- `README.md:34` — "A packaged self-hosted operator Admin Web UI still ships under `/admin` … scheduled
  for removal in P6": **removed in P6.S1**; rewrite or drop.
- `README.md:210` — "The packaged Admin Web UI at `http://127.0.0.1:8000/admin` still loads … paste that
  token into the Admin UI token field": no longer exists.
- `README.md:259` — "The packaged (superseded, P6-removal) Admin Web UI under `/admin`".
- `README.md:222`, `:274`, `:445` — "bearer token required for `/admin/api/*` **when set**" / "Set
  `VOCKY_ADMIN_AUTH_TOKEN` **before exposing**": now unconditional — without the token the surface is
  `503`, with it a bearer is mandatory.
- `README.md:32` and `:430` already read correctly; leave them.

`README.md` is not a generated doc, so edit it directly. **Do not touch `docs/current/*.md`.**

## Boundaries

- **No `doc-new-version`, no edits under `docs/`.** Durable docs are versioned once, at `P12.REVIEW`.
  Append a "Doc impact" line to `phase.md` instead (see below).
- Do not commit, do not run any `workflow.py` state command, do not touch other slices' folders.
- Do not touch `src/vocky/admin_api.py`'s route handlers, the `/api/*` credential middleware, or anything
  in the `/auth/*` path (that is `P12.S3`).
- Do not run `prettier --write` or touch `web/` — that is `P12.S2`.

## Validation

1. `uv run pytest tests/test_public_access.py tests/test_admin_api.py` → green (this is the slice's
   behavioural proof; both branches of the new middleware must be covered).
2. `uv run ruff check src tests` and `uv run ruff format --check src tests` (or whatever the repo's
   `Makefile` lint target actually is — check it, do not invent one).
3. Compose still parses **and** now refuses a missing secret:
   - with the three secrets exported to dummy values → `docker compose -f compose.prod.yml config -q`
     succeeds;
   - with `VOCKY_ADMIN_AUTH_TOKEN` unset → the same command **fails** with the new message.
   - If the `docker compose` CLI is not installed in the sandbox, say so in `result.md` and fall back to a
     `python3 -c 'import yaml…'` parse plus a grep asserting all three `:?` forms are present. Do **not**
     skip the check silently, and do not attempt to start any container.
4. `grep -rn "VOCKY_ADMIN_AUTH_TOKEN" README.md` — every surviving line describes the fail-closed model.

## Deliverables

- `result.md` (free-form): what changed, the chosen status code and why, the compose-interpolation
  extension, the exact validation output, and anything the bring-up (`P12.S4`) must now know.
- Notes appended to `phase.md` § *Findings & Notes* — at minimum: the admin surface is **kept and
  fail-closed**, `VOCKY_ADMIN_AUTH_TOKEN` is now **mandatory** for a production `up` (relevant to S4's
  secret-generation gate), and all three prod secrets now abort Compose when unset.
- A **Doc impact** line appended to `phase.md` § *Doc impact* covering: `architecture.md`'s open question
  *"whether Admin REST outlives the UI it served"* is now **resolved — kept, fail-closed, token
  mandatory**; `security.md`'s defence-in-depth claim about `/admin/api/*` is now actually true in code;
  and `operations.md`'s "missing box secret fails loudly" claim is now true for all three secrets (which
  supersedes the correction `P12.DECOMP` filed).
