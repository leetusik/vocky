# Plan — P12.S3: Rate-limit the public `/auth/*` surface (deferred job D5)

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-mid` (risk `medium`).

## Why now

`POST /auth/signup` (open signup) and `POST /auth/login` (an unauthenticated password grant) are the two
routes that become publicly reachable the moment `P12.S4` brings the site up. vocky has **no server-side
per-IP limiter of any kind** — `grep` for `X-Forwarded-For|X-Real-IP|CF-Connecting-IP|client_ip` across
`src/` returns nothing. `deploy/vocky.conf:50-54` **forbids** an nginx `limit_req_zone` (zone names are
global across the shared edge's whole `conf.d/` tree; a duplicate is a hard `nginx -t` failure that blocks
reload for *every* co-tenant site). So the throttle has to live in the app, and it has to land before the
launch — `intent.md` is explicit that D5 goes **before or with** go-live, not after.

## Design — settled, do not re-litigate

The sibling repo has already shipped this exact limiter at
`/Users/sugang/projects/personal/knowledge/server/auth_api.py:56-157`. **Read it first and mirror its
approach**, adapting to vocky's Starlette idioms. The decisions below are made; implement them.

1. **Handler-level, not middleware.** Call the check at the top of the `signup` and `login` handlers in
   `src/vocky/auth_api.py`, before any DB or password work. *Reason:* five test files build a bare
   `Starlette(routes=auth_routes, …)` with **no middleware** (`tests/test_auth_api.py:18`,
   `test_app_api.py:21`, `test_usage_api.py:41`, `test_accounts_provisioning.py:37`,
   `test_app_feedback_api.py:23`), so a middleware limiter would be invisible to every auth test while
   silently active in `create_app()`. Handler-level is also what `knowledge` does.
2. **Return, don't raise.** `auth_api.py` returns every failure inline as `JSONResponse({"detail": …})`
   (see `_INVALID_CREDENTIALS` at `:43`, the 409 at `:164`, the 400s at `:156`/`:193`). A new exception
   type would have to be registered in `create_app()`'s `exception_handlers` **and** in all five bare test
   apps. Match the file's existing idiom instead.
3. **New module `src/vocky/rate_limit.py`.** Keep `auth_api.py` lean and give tests a seam. Model the
   module's shape on `src/vocky/redis_client.py` (module-global state + a small public surface).
   Public surface:
   - `check_rate_limit(request: Request, *, bucket: str) -> JSONResponse | None` — `None` means allowed.
   - `reset_rate_limits() -> None` — clears all state; used by tests.
   - `client_ip(request: Request) -> str` — exported so it can be unit-tested directly.
4. **Fixed window, in memory.** Module-level `dict[str, tuple[float, int]]` mapping `"<ip>:<bucket>"` →
   `(window_start_monotonic, count)`, using `time.monotonic()`. Roll the window over when
   `now - start >= window`. **Do no `await` anywhere in the check** — that is what makes it atomic under a
   single event loop and lets it skip a lock. Bound memory exactly as `knowledge` does: a
   `_RATE_MAX_KEYS = 20_000` cap, pruning expired keys first and then the oldest half if still capped
   (worst case under-counts; it must never over-count).
   - **Not Redis**, even though `src/vocky/redis_client.py` exists: it would add an `await` and a hard
     Redis dependency to the login path (today `/auth/*` touches only Postgres), and a Redis outage would
     force a fail-open/fail-closed decision this slice should not have to make.
   - **This is only sound because the API runs a single uvicorn process** (`Dockerfile:18` →
     `vocky-server` → `src/vocky/main.py:16-21`, `uvicorn.run(...)` with no `workers=`, no gunicorn, and
     `compose.prod.yml` sets no `command:` override and no `deploy.replicas`). vocky has **never written
     that invariant down**. Add a short comment next to the `uvicorn.run` call in `src/vocky/main.py`
     saying that the in-process auth limiter assumes a single worker, so adding `workers=N` would silently
     divide the limit. That comment is part of this slice.
5. **Client IP resolution**, in this order: `X-Real-IP` → the first comma-segment of `X-Forwarded-For` →
   `request.client.host` → `"unknown"`. Document the trust model in the module docstring: these headers
   are only trustworthy because `vocky-api` publishes **no host port** (`compose.prod.yml:83`) and is
   reachable solely through the edge, which restores the real visitor IP from Cloudflare
   (`deploy/vocky.conf:113-136`) and sets `X-Real-IP` / `X-Forwarded-For` at the **server** level
   (`:164-165`). Locally there is no nginx, so the `request.client.host` fallback must work.
   - **Do not touch `deploy/vocky.conf`.** Its `:157-162` note is load-bearing: the proxy headers are set
     once at server level and the *first* per-`location` `proxy_set_header` silently drops the entire
     inherited set — which would collapse every client onto one bucket. `location /auth/` correctly sets
     none today. Reference this in a comment; change nothing.
6. **Buckets are per `(IP, route)`** — pass `bucket="signup"` and `bucket="login"` so the two are counted
   independently.
7. **Config knobs** on `Settings` (`src/vocky/config.py`), following the existing `Field(default=…,
   alias="VOCKY_…")` + `@property` accessor style (see `:39` and `:63`):
   - `VOCKY_AUTH_RATE_LIMIT`, default **20**
   - `VOCKY_AUTH_RATE_WINDOW_S`, default **900** (15 minutes)
   - A limit `<= 0` **disables** the limiter entirely (the escape hatch, and what a smoke run can set).
   Read them through `get_settings()` inside the check, not at import time.
8. **On limit:** `429` with body `{"detail": "too many requests — please retry later"}` and a
   `Retry-After` header of `max(1, int(window - elapsed))` seconds. Do **not** add `X-RateLimit-*` headers
   — keep the response surface minimal.
9. **Key on IP only, never on email.** `login` deliberately returns an identical 401 for unknown-email and
   wrong-password (`auth_api.py:43`, `:198`) so it leaks no account existence; an email-keyed limiter
   would reintroduce exactly that leak. Checking before any DB work also keeps the 429 timing-independent.
10. **Scope is `signup` + `login` only.** `/auth/logout` and `/auth/me` are authenticated — leave them
    alone. Do not blanket-limit the `/auth/` prefix.

## The test-suite trap — handle it explicitly

`httpx.ASGITransport` injects a fixed `scope["client"] = ("127.0.0.1", 123)` and sends no forwarding
headers, so **every test in the entire suite shares one IP**. Across a pytest session there are roughly
**37 signups** and **3 logins** (heaviest: `test_auth_api.py` 8, `test_app_api.py` 8,
`test_org_credentials_api.py` 6, `test_usage_api.py` 5). A 20/15-min limit would therefore start
returning 429 partway through the session, and `time.monotonic()` never advances 15 minutes during a run.

Fix it by **isolating state per test**, not by loosening the production default: add a small **autouse**
fixture to `tests/conftest.py` that calls `reset_rate_limits()` before each test. Keep it to a few lines
and put it next to the existing fixtures. Do not change any other conftest behaviour.

For tests that need a *low* limit, `tests/conftest.py:47-51` already shows the idiom: set the env var with
`monkeypatch` and call `get_settings.cache_clear()`.

## Tests to add — terse, in `tests/test_auth_api.py`

Follow the file's existing style. A handful of high-value cases, no fixture sprawl (`AGENTS.md`):

1. **Trips and reports:** with a low limit set via env, N allowed requests then a `429` whose body is
   `{"detail": …}` and which carries a sane `Retry-After`.
2. **Per-IP isolation:** a second client built with `httpx.ASGITransport(app=…, client=("10.0.0.2", 1))`
   — or an `X-Real-IP` header — is unaffected while the first is throttled. This is the test that would
   have caught "everyone shares one bucket", the single worst failure mode here.
3. **Per-route isolation:** exhausting `signup` does not throttle `login`.
4. **Disabled:** limit `<= 0` never throttles.

A direct unit test of `client_ip()`'s header precedence is welcome if it stays to a few asserts.

## Boundaries

- Files you may change: `src/vocky/rate_limit.py` (new), `src/vocky/auth_api.py`, `src/vocky/config.py`,
  `src/vocky/main.py` (the one comment), `tests/test_auth_api.py`, `tests/conftest.py` (the autouse
  fixture only), and `.env.example` / `.env.prod.example` if you document the two new knobs there.
- **Do not** touch `deploy/vocky.conf`, `compose.prod.yml`, `.github/`, or anything under `web/` — the
  BFF's own JS limiter (`web/src/lib/rate-limit.ts`) is a separate, deliberately weak layer and aligning
  it is **out of scope**; note it as an open question instead.
- **Do not** edit anything under `docs/`, do not run `doc-new-version`, do not commit, and do not run any
  `scripts/workflow.py` state command. (Closing deferred job **D5** is the orchestrator's job, not yours —
  `promote-deferred` is unavailable because the slice folder already exists.)
- Do not change the existing `/auth/*` response codes, bodies, or the deliberate no-enumeration property.

## Validation — run these and report the actual output

1. `uv run pytest tests/test_auth_api.py` → green, including the new cases.
2. `uv run pytest` (the full suite) → **no worse than the baseline**. Expect ~108 Postgres-dependent
   errors if no database is reachable from your sandbox; what matters is that **no test regresses because
   of the limiter** (this is the specific risk the autouse fixture addresses — confirm it, do not assume
   it). Report the counts you actually see, and say plainly whether a database was available.
3. `uv run --with ruff ruff check src tests` → clean (bare `ruff` is not on PATH in this sandbox).
4. Confirm the disabled path: with `VOCKY_AUTH_RATE_LIMIT=0`, the limiter never throttles.

## Deliverables

- `result.md` (free-form): the mechanism chosen and why, the exact defaults, the client-IP precedence, the
  single-worker assumption you documented, verbatim validation output, and anything `P12.S4` must know
  (in particular: whether a Cloudflare rule is still worth adding as an outer layer, and what limit the
  live smoke should expect).
- Notes appended to `phase.md` § *Findings & Notes*: the limiter's location, its defaults, the
  single-worker invariant, and the test-isolation fixture.
- A **Doc impact** line in `phase.md` § *Doc impact*: `security.md` records the `/auth/*` rate-limit gap as
  accepted "for launch behind Cloudflare" — that gap is now **closed in-app**; `operations.md` gains two
  new tunables. `P12.REVIEW` consolidates it.
