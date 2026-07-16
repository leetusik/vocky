---
doc_id: security
version: v0002
created_at: 2026-07-16T14:20:12+09:00
source: P2.REVIEW
summary: Argon2id passwords, opaque hashed session tokens (30-day TTL), mint-once hashed vk_ project credentials, mandatory ingest auth, no enumeration
previous: v0001_bootstrap
---

# Security

## Status

Covers the authentication and secret-handling posture landed in P2: password hashing, account session tokens, per-project ingest credentials, and the mandatory `/api/*` ingest boundary. Attachment-download authorization and admin-token handling are covered in `architecture.md` / `api.md`.

## Passwords

- Passwords are hashed with **argon2id** (`argon2-cffi`) via `hash_password` and stored only as the argon2 hash in `users.password_hash`. Raw passwords are never stored or logged.
- `POST /auth/signup` requires a password of at least 8 characters (`_EmailPasswordInput`); email is trimmed + lowercased and must contain `@`.
- `verify_password` returns `False` (never raises) on a mismatch or a malformed stored hash, so failures are indistinguishable to the caller.

## No User Enumeration

- `POST /auth/login` returns an **identical** `401 {"detail":"invalid email or password"}` for an unknown email and for a wrong password. The handler always reaches `verify_password` semantics without revealing which check failed, so an attacker cannot use login responses to discover which emails are registered.
- `signup` does surface a distinct `409` on a duplicate email (the account-creation UX needs it); this is an accepted trade-off and is the only place email existence is observable.

## Session Tokens (account auth)

- Login and signup mint an opaque, high-entropy bearer token with `secrets.token_urlsafe(32)`. The raw token is returned **once** in that response and is the account session credential for `/auth/*` and `/app/*`.
- Only `sha256_hex(token)` is persisted in `auth_tokens.token_hash` (UNIQUE); the raw token is never stored. High-entropy tokens make an unsalted sha256 appropriate here (no offline-guessing surface), and it lets lookups be a single indexed equality match.
- Tokens carry a 30-day expiry (`SESSION_TTL`). The active-token lookup requires `expires_at IS NULL OR expires_at > now()`, so expired tokens fail authentication.
- Logout (`POST /auth/logout`) deletes the token row (hard revoke); it is idempotent and always returns `204`.
- `require_user` resolves a token to the caller and their tenant; any miss (absent, malformed, unknown, expired, dangling user/tenant) raises `AuthError`, rendered as a generic `401` with `WWW-Authenticate: Bearer`.

## Per-Project Ingest Credentials

- A project key is minted as `key = "vk_" + generate_opaque_token()`. The plaintext is returned **once**, only in the `POST /app/projects/{id}/credentials` response, and is never recoverable afterward.
- Only `sha256_hex(key)` (`token_hash`, UNIQUE) and a short display `token_prefix = key[:12]` are stored. Credential records and list responses expose `token_prefix` but **never** `token_hash` or the raw key.
- Revocation is a soft-revoke: `DELETE …/credentials/{id}` sets `revoked_at`. The ingest lookup (`get_active_credential_by_token_hash`) filters `revoked_at IS NULL`, so a revoked key fails `/api/*` auth immediately.

## Mandatory `/api/*` Ingest Auth

- Public REST ingestion is **strictly mandatory** credential auth. `ProjectCredentialAuthMiddleware` guards every `/api/*` HTTP request: it extracts the bearer, hashes it, and requires an active (non-revoked) project credential to match. There is **no** token argument and **no** open/unauthenticated fallback — the previous optional static-token model (`VOCKY_API_AUTH_TOKEN`) is retired.
- Missing, malformed, unknown, and revoked credentials **all** answer an identical generic `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`, so a caller cannot distinguish "no key" from "wrong key" from "revoked key".
- The guard is identity-only in P2: it does not stash project/tenant state onto the ASGI scope and does not stamp `last_used_at` (both P3).

## Tenant Isolation

- The `/app/*` control-plane is tenant-scoped. Every per-project read/mutation resolves the project against `ctx.tenant.id` first and answers **404 (never 403)** when the project is missing or belongs to another tenant, so cross-tenant existence is never leaked. Credential endpoints apply the same rule before any credential work, and credential ids are checked against the scoped project's own list before revoke.

## Secret-Exposure Discipline

- Response serializers never emit secrets: `serialize_user` omits `password_hash`; `serialize_tenant`/`serialize_project` carry no secret; `serialize_credential` omits `token_hash` and the raw key; token/credential records carry only `token_prefix`.
- Raw session tokens and project keys are returned exactly once (at mint time) and only as sha256 hashes thereafter; the DB never holds a recoverable password, session token, or ingest key.

## Admin Surface (unchanged)

- `AdminBearerAuthMiddleware` and `VOCKY_ADMIN_AUTH_TOKEN` are untouched by the accounts work; `/admin/api/*` keeps its own separate bearer boundary. Reshaping the operator surface is P4.
