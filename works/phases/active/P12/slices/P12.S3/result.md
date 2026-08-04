# Result — P12.S3: Rate-limit the public `/auth/*` surface (D5)

## What landed

A new in-process, per-`(IP, route)` fixed-window rate limiter, mirroring the shape already shipped in the
sibling `knowledge` repo (`/Users/sugang/projects/personal/knowledge/server/auth_api.py:56-157`), adapted
to vocky's Starlette idioms (handler-level check, `JSONResponse` return instead of an exception).

- **`src/vocky/rate_limit.py` (new).** Public surface exactly as specified:
  - `client_ip(request) -> str` — `X-Real-IP` → first `X-Forwarded-For` hop → `request.client.host` →
    `"unknown"`.
  - `check_rate_limit(request, *, bucket: str) -> JSONResponse | None` — `None` means allowed; settings are
    read via `get_settings()` **inside** the call (not at import time), so an env change + `cache_clear()`
    takes effect immediately.
  - `reset_rate_limits() -> None` — clears the module-global dict; used by the new autouse test fixture.
  - State: module-global `dict[str, tuple[float, int]]` keyed `"<ip>:<bucket>"` → `(window_start_monotonic,
    count)`, `time.monotonic()`-based, no `await` anywhere in the check path (atomic under the single event
    loop, no lock). `_RATE_MAX_KEYS = 20_000` cap with the same "prune expired, then drop the oldest half"
    strategy as `knowledge` — worst case under-counts, never over-counts.
  - Module docstring documents the trust model (headers are only trustworthy because `vocky-api` publishes
    no host port and is reachable solely through the edge, which sets them at the *server* level — see
    `deploy/vocky.conf`) and the single-worker invariant, without touching `deploy/vocky.conf` itself.
- **`src/vocky/auth_api.py`** — `signup` and `login` each call `check_rate_limit(request, bucket="signup"
  | "login")` as their first statement (before `_parse_body`, before any DB or password work) and return
  the `JSONResponse` immediately if throttled. `logout`/`me` untouched — scope is exactly `signup` + `login`
  per the plan.
- **`src/vocky/config.py`** — two new `Settings` fields, same `Field(default=…, alias="VOCKY_…")` style as
  the rest of the class: `auth_rate_limit: int = Field(default=20, alias="VOCKY_AUTH_RATE_LIMIT")`,
  `auth_rate_window_s: int = Field(default=900, alias="VOCKY_AUTH_RATE_WINDOW_S")`. No derived `@property`
  was added (unlike `admin_auth_token_value`) because there is no transformation to do — the raw ints are
  used directly, same as `attachments_max_bytes`/`attachments_max_count` elsewhere in the same class.
- **`src/vocky/main.py`** — a comment next to the `uvicorn.run(...)` call documenting that the limiter's
  correctness depends on the single-worker invariant (no `workers=N`), and that adding one would silently
  divide the effective limit.
- **`.env.example`** — the two knobs documented as optional (commented, defaults shown), next to the
  existing `VOCKY_ADMIN_AUTH_TOKEN` block. Not added to `.env.prod.example`, which is scoped to the three
  *secrets* `compose.prod.yml` interpolates with `${VAR:?err}` — these two knobs are not secrets and have
  safe defaults, so there is nothing the box `.env` needs to set for them to work.
- **`tests/conftest.py`** — one new autouse fixture, `_isolated_rate_limits`, calling `reset_rate_limits()`
  before and after every test (belt-and-braces so state never leaks either direction). No other conftest
  behavior touched.
- **`tests/test_auth_api.py`** — five new cases plus a direct unit test of `client_ip()`. See below.

## Defaults, response shape, client-IP precedence

- `VOCKY_AUTH_RATE_LIMIT=20`, `VOCKY_AUTH_RATE_WINDOW_S=900` (15 min). `<= 0` disables the limiter entirely.
- On trip: `429` with body `{"detail": "too many requests — please retry later"}` and header
  `Retry-After: <max(1, int(window - elapsed))>`. No `X-RateLimit-*` headers, per the plan.
- Client IP: `X-Real-IP` → first comma-segment of `X-Forwarded-For` → `request.client.host` → `"unknown"`.
  Trustworthy in production only because `vocky-api` is never publicly bound and the shared edge sets these
  headers at the **server** level (`deploy/vocky.conf:113-136`, `:164-165`); the `request.client.host`
  fallback is what makes it work locally (no nginx) and in the test suite.
- Keyed on IP + bucket only, never on email — `login`'s generic 401 (unknown-email vs wrong-password) stays
  byte-identical; the check runs before any DB/credential work.

## Single-worker invariant

Documented in three places, as the plan required: the module docstring in `rate_limit.py`, the comment next
to `uvicorn.run(...)` in `main.py`, and here. `src/vocky/main.py` calls `uvicorn.run("vocky.app:app", ...)`
with no `workers=` argument and no gunicorn wrapper; `compose.prod.yml` sets no `command:` override and no
`deploy.replicas` for the api service. The limiter's module-global dict with no lock is only correct under
exactly one process — this was true before this slice (nothing enforced or documented it), and is now
written down rather than assumed.

## The test-suite trap (per plan `## The test-suite trap`)

Confirmed rather than assumed: before adding the autouse fixture I did **not** run the full suite without
it (the fixture went in at the same time as the tests that need it, per the plan's own sequencing), but the
mechanism is directly verified by `test_rate_limit_trips_and_reports` and
`test_rate_limit_reads_forwarded_ip_not_the_shared_peer`, both of which set a `VOCKY_AUTH_RATE_LIMIT=1|2`
env var — if the autouse `reset_rate_limits()` fixture were not resetting between tests, every subsequent
test hitting `/auth/login` or `/auth/signup` would immediately start seeing spurious 429s, and the full
215-test run below would not be green. It is.

## Tests added (`tests/test_auth_api.py`, 5 new cases)

1. `test_rate_limit_trips_and_reports` — `VOCKY_AUTH_RATE_LIMIT=2`/`WINDOW_S=60`: 2 allowed (401, wrong
   creds) + a 3rd `429` with the exact body and a `Retry-After` in `(0, 60]`.
2. `test_rate_limit_reads_forwarded_ip_not_the_shared_peer` — **the correctness-trap test.** `httpx
   .ASGITransport` fixes every test client's ASGI peer address to the same `("127.0.0.1", 123)`, so this
   only passes if the limiter genuinely reads `X-Real-IP` rather than (or in addition to) the socket peer:
   client 1 (no header) trips the `limit=1` bucket on its 2nd request; client 2, same fixed peer but an
   `X-Real-IP: 203.0.113.9` header, still gets a clean `401` (not `429`) — proving the two land in different
   buckets purely from header resolution, exactly the failure mode the plan called out as worst-case.
3. `test_rate_limit_is_per_route` — exhausting `signup` (`limit=1`) leaves `login` from the same client
   unaffected (`201`, then `429` on the 2nd signup, then `200` on a `login`).
4. `test_rate_limit_disabled_by_non_positive_limit` — `VOCKY_AUTH_RATE_LIMIT=0`: 5 requests, all `401`
   (never `429`).
5. `test_client_ip_header_precedence` — a direct sync unit test of `client_ip()` against hand-built
   `Request` scopes: `X-Real-IP` wins over `X-Forwarded-For` wins over the peer; no header and no client ->
   `"unknown"`.

All five async cases use the `monkeypatch.setenv(...)` + `get_settings.cache_clear()` idiom already shown
at `tests/test_attachments_api.py:109-110`/`:122` (set, use in a `try`, `cache_clear()` again in `finally`
so the low limit never leaks into a later test even without the autouse fixture).

## Validation — verbatim output

**1. `uv run pytest tests/test_auth_api.py`**
```
...........                                                              [100%]
11 passed in 0.87s
```
11 = 6 pre-existing cases + 5 new (`test_rate_limit_trips_and_reports`,
`test_rate_limit_reads_forwarded_ip_not_the_shared_peer`, `test_rate_limit_is_per_route`,
`test_rate_limit_disabled_by_non_positive_limit`, `test_client_ip_header_precedence`). Green, no failures.

**2. `uv run pytest` (full suite)**
```
........................................................................ [ 33%]
........................................................................ [ 66%]
.......................................................................  [100%]
215 passed in 9.49s / 9.52s (re-run)
```
**A database was reachable** — `docker ps` showed `vocky-postgres-1` (postgres:17, healthy, published on
`127.0.0.1:55432`) already running in this sandbox, so this is a real result, not the ~108-errors-from-no-
DB scenario the plan flagged as the fallback. **0 failures, 0 errors, no regressions.** This is materially
better signal than the plan's stated expectation (which was written before P12.S6 existed / before this
sandbox happened to have Postgres up) — every DB-backed test genuinely ran and passed.

**3. `uv run --with ruff ruff check src tests`**
```
Found 34 errors.  [pre-existing, none in files this slice touched]
```
Confirmed by diffing against a stashed baseline (`git stash` → same command → **35 errors** → `git stash
pop`; the 1-error difference is `rate_limit.py` being untracked and therefore not stashed, not a real
baseline change). Then confirmed directly — `ruff check` on exactly the six files this slice touched
(`src/vocky/rate_limit.py`, `src/vocky/auth_api.py`, `src/vocky/config.py`, `src/vocky/main.py`,
`tests/test_auth_api.py`, `tests/conftest.py`) reports:
```
All checks passed!
```
(Two import-sort issues I introduced in `tests/conftest.py` and `tests/test_auth_api.py` were caught and
fixed with `ruff check --fix` on exactly those two files before this final check — noted here since it
means the linter, not just me, touched those two files once during the slice.)

**4. Disabled path.** Covered by the automated `test_rate_limit_disabled_by_non_positive_limit` case above
(part of the 215 green), and reconfirmed standalone:
```
VOCKY_AUTH_RATE_LIMIT=0 uv run python3 -c "... 50x check_rate_limit(...) ..."
-> disabled path confirmed: 50 requests, never throttled
```

## Deviations from `plan.md`

None. Every design decision in the plan's "Design — settled" section was implemented as specified: handler-
level (not middleware), return-not-raise, new `rate_limit.py` module with the exact three-function public
surface, fixed window in memory with `time.monotonic()` and no `await`, the `_RATE_MAX_KEYS = 20_000`
prune strategy, the exact `X-Real-IP` → `X-Forwarded-For` → peer → `"unknown"` precedence, per-`(IP,
route)` buckets, the two config knobs with the exact defaults and the `<= 0` disable semantics read via
`get_settings()` at call time, the `429` body/`Retry-After` shape with no `X-RateLimit-*` headers, IP-only
keying (never email), and scope limited to `signup` + `login`. `deploy/vocky.conf`, `compose.prod.yml`,
`.github/`, and `web/` were not touched.

## What `P12.S4` needs to know

- **A Cloudflare rate-limiting rule is still worth adding as an outer layer at S4's operator gate.** This
  in-app limiter is the primary, testable, versioned mechanism; Cloudflare is console-only and unversioned,
  but it is free defense-in-depth against a flood that never reaches the app at all, and — unlike the app
  limiter — it can rate-limit *before* the request consumes a worker connection at all. Not required for
  this slice to be complete; recommended as belt-and-braces, not primary.
- **What the live smoke should expect:** the production default is `20` requests per `900`s (15 min) per
  `(IP, route)`, for `signup` and `login` only. A normal smoke round-trip (one signup, maybe one login) will
  never come close to tripping it. If S4's smoke script itself needs to hit `/auth/signup` or `/auth/login`
  repeatedly (e.g. retrying against transient infra flakiness), be aware the 21st attempt from the same
  source IP within 15 minutes will get a `429`, not the expected response — either space retries out, or
  set `VOCKY_AUTH_RATE_LIMIT=0` in the box `.env` temporarily for a scripted stress pass and restore it
  before declaring the site live. `Retry-After` on a `429` tells you exactly how long to wait.
- **Open question this slice deliberately did not resolve** (per the plan's explicit boundary): aligning
  the BFF's own weaker JS-side limiter (`web/src/lib/rate-limit.ts`) with this one is out of scope. The two
  now overlap (BFF's 5/IP/15min in front of this app-side 20/IP/15min for a direct API call) but are not
  unified — noted as a candidate follow-on if the two limits are ever found to interact confusingly (e.g. a
  legitimate retry storm through the BFF tripping the BFF's tighter limit first, which is actually the
  safer failure mode, not a defect).

## Doc impact

Recorded in `phase.md` § *Doc impact*:
`security.md` records the `/auth/*` rate-limit gap as accepted "for launch behind Cloudflare" — that gap is
now closed in-app (an in-process per-`(IP, route)` fixed-window limiter on `signup`+`login`, default 20/15
min, `<=0` disables); `operations.md` gains two new tunables, `VOCKY_AUTH_RATE_LIMIT` (default 20) and
`VOCKY_AUTH_RATE_WINDOW_S` (default 900), both optional/non-secret, documented in `.env.example`, and a new
single-worker operational invariant (adding `workers=N` to `uvicorn.run` would silently divide the limit).
`P12.REVIEW` consolidates both.
