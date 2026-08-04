"""In-process per-IP fixed-window rate limiter for the public ``/auth/*`` grant.

WHY HERE, NOT AT THE EDGE. `POST /auth/signup` (open signup) and
`POST /auth/login` (an unauthenticated password grant) are about to become
publicly reachable. `deploy/vocky.conf` forbids an nginx `limit_req_zone` in
this vhost — zone and location names are global across the shared edge's
whole `conf.d/` tree, so a duplicate is a hard `nginx -t` failure that blocks
reload for *every* co-tenant site. So the throttle lives in the app instead.

TRUST MODEL for the client IP (see `client_ip` below). Keyed on
``X-Real-IP`` first, then the first hop of ``X-Forwarded-For``, then the
ASGI peer address. This is only trustworthy because ``vocky-api`` publishes
no host port (``compose.prod.yml``) and is reachable solely through the
shared edge, which restores the real visitor IP from Cloudflare
(``deploy/vocky.conf``) and sets ``X-Real-IP`` / ``X-Forwarded-For`` at the
**server** level (not per-``location`` — the first per-location
``proxy_set_header`` would silently drop the whole inherited set, which is
exactly why ``location /auth/`` sets none of its own; do not add one).
Locally there is no nginx in front, so the ASGI peer-address fallback is
what makes the limiter still work in dev and in tests.

SINGLE-WORKER INVARIANT. This module is only correct because ``vocky-api``
runs as a single uvicorn process with no ``workers=N`` (see the comment next
to the ``uvicorn.run`` call in ``vocky.main``). State is a plain
module-global dict with no lock; the check performs no ``await`` so it runs
atomically under the single event loop. Splitting into multiple workers (or
processes) would silently divide the limit across independent copies of this
dict.

GENERIC-401 SAFETY. Buckets are keyed on the client IP only, never on the
submitted email — an email-keyed limiter would reintroduce the exact account-
enumeration leak that ``login``'s identical generic 401 exists to avoid. The
check also runs before any DB or password work, so a 429 never turns into a
timing side channel on top of the credential path.
"""

from __future__ import annotations

import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from vocky.config import get_settings

# key ("<ip>:<bucket>") -> (window_start_monotonic, count_in_window)
_rate_windows: dict[str, tuple[float, int]] = {}

# Defensive cap so a distributed flood of distinct IPs cannot grow the dict
# without bound. Well above any plausible legitimate concurrent-client count.
_RATE_MAX_KEYS = 20_000


def client_ip(request: Request) -> str:
    """Return the real client IP behind the edge — see the module TRUST MODEL."""

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    client = request.client
    return client.host if client else "unknown"


def _prune_rate_windows(now: float, window: float) -> None:
    """Bound memory: drop expired windows, and if still capped, the oldest ones.

    Only does work once the dict is large — expired keys otherwise roll over
    lazily on access, so this is a defensive memory bound, not correctness.
    """

    if len(_rate_windows) < _RATE_MAX_KEYS:
        return
    for key in [k for k, (start, _) in _rate_windows.items() if now - start >= window]:
        del _rate_windows[key]
    if len(_rate_windows) >= _RATE_MAX_KEYS:
        # An active flood from many live IPs. Drop the oldest half; the worst
        # case is a few counters resetting early, which only ever
        # under-counts — it must never over-count.
        oldest = sorted(_rate_windows, key=lambda k: _rate_windows[k][0])
        for key in oldest[: _RATE_MAX_KEYS // 2]:
            del _rate_windows[key]


def check_rate_limit(request: Request, *, bucket: str) -> JSONResponse | None:
    """Fixed-window per-``(IP, bucket)`` throttle. ``None`` means allowed.

    Settings are read at call time (``get_settings()``, not at import time) so
    a test or an operator smoke can force a low limit via the env. A tripped
    request answers 429 with a generic body and a ``Retry-After`` header
    (seconds until the window resets); it never touches the DB or the
    credential path — callers must invoke this before any of that work.
    """

    settings = get_settings()
    limit = settings.auth_rate_limit
    if limit <= 0:  # disabled — the escape hatch, e.g. for a smoke run
        return None
    window = float(settings.auth_rate_window_s)
    now = time.monotonic()
    _prune_rate_windows(now, window)

    key = f"{client_ip(request)}:{bucket}"
    start, count = _rate_windows.get(key, (now, 0))
    if now - start >= window:  # window rolled over
        start, count = now, 0
    count += 1
    _rate_windows[key] = (start, count)

    if count > limit:
        retry_after = max(1, int(window - (now - start)))
        return JSONResponse(
            {"detail": "too many requests — please retry later"},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    return None


def reset_rate_limits() -> None:
    """Clear all rate-limit state. Used by tests to isolate them from each other."""

    _rate_windows.clear()
