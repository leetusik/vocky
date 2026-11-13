# Result — P2.S2: Account auth (signup / login / session tokens + user-auth guard)

**Status: done.** Shipped the account-auth surface on top of S1's `AccountsService`:
email+password signup/login issuing opaque DB-backed bearer tokens, plus the reusable
`require_user` guard S3/S4/P4/P5 will import. Full suite green (145 passed).

## Shipped surface

New files:
- `src/vocky/accounts/security.py` — pure primitives: `hash_password` / `verify_password`
  (argon2id via `argon2-cffi`; `verify_password` returns `False`, never raises, on mismatch
  or malformed hash), `generate_opaque_token()` (`secrets.token_urlsafe(32)`),
  `sha256_hex(raw)` (hex sha256 of the raw token — the at-rest hash).
- `src/vocky/accounts/auth.py` — the reusable guard: `@dataclass AuthContext(user, tenant)`,
  `class AuthError(Exception)`, `extract_bearer_token(request) -> str | None` (scheme-insensitive
  `Bearer`), `async require_user(request) -> AuthContext`, `async auth_error_handler(request, exc)`
  (generic 401 `{"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer`). `require_user` does NOT
  touch `last_used_at` (deferred to P3).
- `src/vocky/auth_api.py` — `SESSION_TTL = timedelta(days=30)`, Pydantic `SignupInput`/`LoginInput`
  (shared `_EmailPasswordInput`: email trimmed+lowercased, must contain `@`, non-empty; password
  `min_length=8`; no `EmailStr` so no email-validator dep), `serialize_user`/`serialize_tenant`
  (never emit `password_hash`/`token_hash`), the four handlers, and `routes`.
- `tests/test_auth_api.py` — terse in-process ASGI tests (local `make_auth_app()`,
  `httpx.ASGITransport`, `configured_database`).

Modified:
- `src/vocky/app.py` — registered `*auth_routes` in `create_app()`'s `routes=[...]` (before
  `admin_routes`) and passed `exception_handlers={AuthError: auth_error_handler}` to `Starlette(...)`.
  Both existing middlewares untouched: `/auth/*` matches neither `is_api_path` nor `is_admin_api_path`,
  so signup/login are public.
- `pyproject.toml` / `uv.lock` — `uv add argon2-cffi` (argon2id, `argon2-cffi==25.1.0`). No new env var.

## `/auth/*` contract (for S3/S4 + P4/P5)

- `POST /auth/signup` `{email, password}` → **201** `{token, user:{id,email,created_at},
  tenant:{id,name,created_at}}`. Provisions user + tenant (`"<email-local-part>'s workspace"`) +
  owner membership, then mints a token. `409 {"detail":"a user with this email already exists"}`
  on duplicate email; `400` on bad body.
- `POST /auth/login` `{email, password}` → **200** `{token, user, tenants:[...]}`. Unknown-email and
  wrong-password both return an **identical** `401 {"detail":"invalid email or password"}`
  (no user enumeration); `400` on bad body.
- `POST /auth/logout` (`Authorization: Bearer <token>`) → **204**, idempotent (deletes the hashed
  token row; a missing/absent token still 204).
- `GET /auth/me` (`Authorization: Bearer <token>`) → **200** `{user, tenants:[...]}`; missing/invalid/
  expired token → `401 {"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer` via `AuthError`.

## Reuse surface (import paths)

- Guard: `from vocky.accounts.auth import require_user, AuthContext, AuthError, auth_error_handler`.
  `require_user(request)` raises `AuthError` on any miss; register `{AuthError: auth_error_handler}`
  in the hosting app's `exception_handlers` (already done in `create_app()`).
- Primitives (S4 reuses for `vk_...` project credentials):
  `from vocky.accounts.security import sha256_hex, generate_opaque_token, hash_password,
  verify_password`.
- `SESSION_TTL` lives in `vocky.auth_api`.

## Security notes

- Raw tokens generated with `secrets.token_urlsafe(32)`; only `sha256_hex(raw)` is persisted
  (`create_auth_token`, `expires_at = utc_now() + SESSION_TTL`). Passwords hashed argon2id.
- No response path serializes `password_hash` or any `token_hash` (test asserts this on signup,
  login, and `me` bodies).

## Validation

- `uv add argon2-cffi` + `uv sync` — argon2-cffi 25.1.0 installed.
- `uv run pytest tests/test_auth_api.py` — **6 passed**.
- `uv run pytest` — **145 passed** (full suite green).
- `python3 scripts/workflow.py validate` — passed.

## Deviations from plan.md

None. Implemented components 1–5 as specified. Two within-intent choices: `require_user` and the `me`
handler load the tenant list via `get_accounts_service()` (no new state on `request.state` yet — S3/S4
can add it); `format_pydantic_error` and `utc_now` are imported from `vocky.api` and
`vocky.persistence.models` respectively rather than re-defined, avoiding duplication without touching
those files.

## Doc impact (recorded to phase.md; NOT versioned here)

Appended a note to the phase "Doc impact" list: **api** — `/auth/signup|login|logout|me` contract +
status codes; **security** — argon2id password hashing, opaque session tokens stored as sha256 hash
with a 30-day TTL. No `doc-new-version` run (review slice consolidates). `docs/` untouched.

## Boundary honored

Did not touch `src/vocky/auth.py`, the `/api/*` middleware wiring, `src/vocky/api.py` (import-only),
the `feedback_events` schema, or `docs/`.
