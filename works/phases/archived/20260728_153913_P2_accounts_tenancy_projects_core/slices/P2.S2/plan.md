# Plan — P2.S2: Account auth (signup / login / session tokens + user-auth guard)

**Slice job:** Make the S1 identity layer usable — email+password **signup/login** issuing **opaque
DB-backed bearer tokens**, plus the reusable **`require_user` guard** for S3/S4/P4/P5. Auth surface
only. Read `works/phases/active/P2/phase.md` first (confirmed decisions + S1's session-token and
`create_tenant_with_owner` conventions). Security-sensitive — get the details right.

Builds on S1's `AccountsService` (in `src/vocky/accounts/service.py`): `create_user` (→
`DuplicateEmailError`), `create_tenant_with_owner(user_id, name) -> (TenantRecord, TenantMemberRecord)`,
`get_user_by_email` (UserRecord carries `password_hash`), `get_user_by_id`, `create_auth_token`,
`get_active_auth_token_by_hash`, `delete_auth_token`, `list_tenants_for_user`. `get_accounts_service()`
is the factory. Session-token convention: caller generates a high-entropy token, stores **sha256 hex**;
active lookup filters `expires_at IS NULL OR > now()`.

## New dependency

`uv add argon2-cffi` (argon2id). No new env var.

## Components

**1. `src/vocky/accounts/security.py` (new)** — pure primitives (S4 reuses `sha256_hex`):
- `hash_password(password) -> str` — `argon2.PasswordHasher().hash(...)`.
- `verify_password(password_hash, password) -> bool` — `.verify(...)`, catch
  `argon2.exceptions.VerifyMismatchError`/`InvalidHashError` → `False`.
- `generate_opaque_token() -> str` — `secrets.token_urlsafe(32)`.
- `sha256_hex(raw) -> str` — `hashlib.sha256(raw.encode()).hexdigest()`.

**2. `src/vocky/accounts/auth.py` (new)** — reusable guard (S3/S4 import):
- `@dataclass AuthContext(user: UserRecord, tenant: TenantRecord)`; `class AuthError(Exception)`.
- `extract_bearer_token(request) -> str | None` (scheme-insensitive `Bearer`).
- `async def require_user(request) -> AuthContext`: extract → `sha256_hex` →
  `get_active_auth_token_by_hash` (None → `AuthError`) → `get_user_by_id` (None → `AuthError`) →
  tenant via `list_tenants_for_user(user.id)[0]` → `AuthContext`. Do **not** touch `last_used_at`
  (defer to P3).
- `async def auth_error_handler(request, exc) -> JSONResponse` — `{"detail":"Unauthorized"}`, 401,
  `WWW-Authenticate: Bearer`.

**3. `src/vocky/auth_api.py` (new)** — routes + handlers, mirroring `src/vocky/api.py`
(`await request.json()` guarded by `JSONDecodeError`; Pydantic `.model_validate` +
`format_pydantic_error`; `JSONResponse({"detail":...}, status_code=...)`):
- `SignupInput{email,password}` / `LoginInput{email,password}` validators: email trimmed+lowercased,
  contains `@`, non-empty; password `min_length=8`. No `EmailStr` (avoid email-validator dep).
- `serialize_user(UserRecord)->{id,email,created_at}`, `serialize_tenant(TenantRecord)->{id,name,created_at}`.
  **Never** emit `password_hash` or any `token_hash`.
- `POST /auth/signup` → hash → `create_user` (catch `DuplicateEmailError` → **409**) →
  `create_tenant_with_owner(user.id, f"{email-local-part}'s workspace")` → mint token
  (`generate_opaque_token`; store `sha256_hex`; `expires_at=utc_now()+SESSION_TTL`) → **201**
  `{token, user, tenant}`.
- `POST /auth/login` → `get_user_by_email` (None→**401**) → `verify_password` (False→**401**) → mint
  token → **200** `{token, user, tenants:[...]}`. Identical generic 401 for unknown-email vs
  bad-password (no enumeration).
- `POST /auth/logout` → `delete_auth_token(sha256_hex(extract_bearer_token))` → **204** (idempotent).
- `GET /auth/me` → `require_user` → **200** `{user, tenants:[...]}`.
- `SESSION_TTL = timedelta(days=30)`. `routes=[Route("/auth/signup",POST), Route("/auth/login",POST),
  Route("/auth/logout",POST), Route("/auth/me",GET)]`.

**4. `src/vocky/app.py` (modify)** — import `auth_api.routes`, add to the `routes=[...]` list; pass
`exception_handlers={AuthError: auth_error_handler}` to `Starlette(...)`. Leave both existing
middlewares untouched (`/auth/*` matches neither path predicate → signup/login public).

**5. `tests/test_auth_api.py` (new, terse)** — mirror `tests/test_user_feedback_api.py`'s in-process
ASGI pattern (local `make_auth_app()` = `Starlette(routes=auth_routes,
exception_handlers={AuthError: auth_error_handler})`, `httpx.ASGITransport`+`AsyncClient`,
`configured_database`, `@pytest.mark.anyio`). Cases: signup 201 (token + owner tenant created);
duplicate email 409; login ok / wrong-password 401 / unknown-email 401 (identical body); `me` w/ token
200, w/o token 401; logout 204 then `me` with old token 401; assert no `password_hash`/`token_hash`
in any body. Lean — no fixture sprawl.

## Do NOT touch

`src/vocky/auth.py` (static-token middleware — S4), `/api/*` middleware wiring, `src/vocky/api.py`,
`feedback_events`, `docs/`. No `doc-new-version` (append Doc-impact notes to `phase.md` only).

## Verification (before returning)

- `uv sync` picks up `argon2-cffi`; `uv run pytest tests/test_auth_api.py` passes; full
  `uv run pytest` stays green. If Postgres isn't reachable, still write all code and return
  `blocked`/`needs_operator` with what's needed — do not fake green.

## Deliverables

Write `result.md` (free-form: shipped surface, the `/auth/*` contract, `require_user`/`AuthContext`
import path S3/S4 use, any surfaced risk). Append cross-slice notes to `phase.md`: the `/auth/*`
contract + status codes, the `require_user`/`AuthContext`/`AuthError` reuse surface (import path),
`security.py` primitives (`sha256_hex`, `generate_opaque_token` — S4 reuses), and `SESSION_TTL`.
Do NOT commit or transition status. Escalate with findings if the slice exceeds the plan's depth;
`blocked`/`needs_operator` with specifics on an impediment you can't resolve.
