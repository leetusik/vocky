---
doc_id: security
version: v0004
created_at: 2026-07-16T18:52:17+09:00
source: P7.REVIEW
summary: P7: /mcp requires a per-project vk_ credential (same guard/401/last_used_at as /api/*); DNS-rebinding on; static token retired
previous: v0003_p3_project-scoped_read_authz_404-never-403_on_api_project_and_app_feedback_one_vk__key_captures_reads_manages_its_project_no_per-credential_scopes_best-effort_last_used_at_stamping_tightened_project-scoped_self-read
---

# Security

## Status

Covers the authentication and secret-handling posture landed in P2 (password hashing, account session tokens, per-project ingest credentials, the mandatory `/api/*` ingest boundary) plus the P3 authorization posture for the new feedback surfaces: project-scoped read/manage authorization that answers 404-never-403 on cross-project/cross-tenant ids, the single-key project read/manage surface, best-effort `last_used_at` stamping, and the tightened project-scoped self-read. As of **P7** it also covers the MCP capture endpoint: `/mcp` is guarded by the same mandatory per-project `vk_` credential auth as `/api/*`, and its Streamable-HTTP transport carries DNS-rebinding protection. Attachment-download authorization and admin-token handling are covered in `architecture.md` / `api.md`.

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

## Mandatory `/api/*` and `/mcp` Ingest Auth

- Public REST ingestion is **strictly mandatory** credential auth. `ProjectCredentialAuthMiddleware` guards every `/api/*` HTTP request: it extracts the bearer, hashes it, and requires an active (non-revoked) project credential to match. There is **no** token argument and **no** open/unauthenticated fallback — the previous optional static-token model (`VOCKY_API_AUTH_TOKEN`) is retired.
- As of **P7** the same guard also covers the **entire `/mcp` MCP endpoint** (the middleware predicate is `is_api_path(p) or is_mcp_path(p)`, where `is_mcp_path` matches `/mcp` and `/mcp/…`). The MCP `initialize` handshake is included, so an unauthenticated agent cannot even open a session; identical resolution, `401`, scope stash, and `last_used_at` stamp as `/api/*`. The retired **static `VOCKY_MCP_AUTH_TOKEN`** is **not** revived — MCP auth is now per-project `vk_` credentials.
- Missing, malformed, unknown, and revoked credentials **all** answer an identical generic `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`, so a caller cannot distinguish "no key" from "wrong key" from "revoked key".
- As of P3 the guard also **threads project scope**: on a successful auth it stashes the resolved `ProjectCredentialRecord` on the ASGI scope under the namespaced key `vocky.project_credential` (read by handlers via `get_request_credential`), and best-effort stamps the credential's `last_used_at` (see below). The namespaced scope key (not `request.state`) is deliberate — it survives any Starlette `scope["state"]` re-init inside the middleware stack, and it also survives crossing into the mounted FastMCP sub-app so an MCP tool can read the credential back off `ctx.request_context.request`.

## MCP Endpoint Transport Security (P7)

- The `/mcp` FastMCP Streamable-HTTP transport enables **DNS-rebinding protection** by default: a strict `Host`/`Origin` allowlist (localhost — `127.0.0.1:*`, `localhost:*`, `[::1]:*` — always allowed, extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`). A publicly-exposed `/mcp` must add its public `Host` (with port) to the allowlist or the transport rejects the request. This is defense against a browser being tricked into posting to a local MCP server; it is orthogonal to the credential auth above (which is the actual access boundary).

## Project-Scoped Read/Manage Authorization (P3)

P3 adds project-scoped feedback surfaces; all of them enforce authorization in the handler and answer **404 (never 403)** on any id outside the caller's scope, so cross-project/cross-tenant existence is never leaked (the same stance as D-P2-5):

- **`/api/project/feedback` (project-credential authed, single-project).** The authenticating project comes from the credential the ingest middleware resolved — never a path or query parameter. The list endpoint **forces** `filters.project_id = credential.project_id`, overriding any caller-supplied value, so a key can only ever read its own project. Every per-feedback op (`get` / `patch` / `delete` / `comments` / `attachment`) loads through `_load_project_feedback`, which returns the record only when `record.project_id == credential.project_id`, else `None` → 404; for mutating ops the ownership check runs **before** the mutation or any attachment-linkage read. Because `project_credentials.project_id` is `NOT NULL`, the forced filter can never degrade to an unscoped read, and legacy NULL-`project_id` feedback rows (None) never equal a real project id.
- **`/app/feedback` (session authed, cross-project).** Every handler resolves the caller's project set via `list_projects_for_tenant(ctx.tenant.id)` and scopes reads to it; any feedback outside that set (including legacy NULL-project rows) answers 404 via `_load_scoped_feedback`. Optional `?project_id` narrowing validates membership: malformed → 400, not-owned/unknown → 404. The list normalizer (`normalize_list_query`) does not read `project_id`/`project_ids`/`search` from the query string, so a caller cannot inject a project filter to escape their tenant scope — the handler sets the scope authoritatively.
- **Tightened self-read (D-P3-6).** `GET /api/feedback` (end-user self-read, scoped by required `user_id` + `source_product`) now additionally scopes to the authenticating credential's project as defense in depth, so a product key cannot surface another project's rows even under a colliding `(user_id, source_product)`. Its sibling attachment download (`GET /api/feedback/{id}/attachments/{id}`) remains scoped by `user_id` + `source_product` only and additionally requires the exact feedback + attachment UUIDs; extending project scope to it is a possible future hardening.

## Single-Key Project Read/Manage Surface (P3, D-P3-2)

- One `vk_` project credential does **everything for its project**: capture **and** project-scoped read + manage on `/api/project/feedback`. There are **no per-credential scopes** in the MVP — the authorization boundary is the credential's project, not a per-key permission set. A future least-privilege split would add scopes without changing the project boundary.

## Best-Effort `last_used_at` Stamping (P3)

- On each successful `/api/*` **or `/mcp`** ingest auth, `ProjectCredentialAuthMiddleware` stamps the credential's `last_used_at`; on each authenticated `/auth/*`/`/app/*` call, `require_user` stamps the auth token's `last_used_at`. Both are one indexed `UPDATE` by PK.
- Both stamps are wrapped in `try/except AccountsPersistenceError` → log and continue, so a stamping failure **never** turns an otherwise-valid ingest or authenticated request into a 500. There is no throttle (stamp-always); a throttle is a possible future optimization if the write becomes hot. The usage endpoints surface these values (operational visibility only — see D-P3-5, no metering/billing).

## Tenant Isolation

- The `/app/*` control-plane is tenant-scoped. Every per-project read/mutation resolves the project against `ctx.tenant.id` first and answers **404 (never 403)** when the project is missing or belongs to another tenant, so cross-tenant existence is never leaked. Credential endpoints apply the same rule before any credential work, and credential ids are checked against the scoped project's own list before revoke.

## Secret-Exposure Discipline

- Response serializers never emit secrets: `serialize_user` omits `password_hash`; `serialize_tenant`/`serialize_project` carry no secret; `serialize_credential` omits `token_hash` and the raw key; token/credential records carry only `token_prefix`.
- Raw session tokens and project keys are returned exactly once (at mint time) and only as sha256 hashes thereafter; the DB never holds a recoverable password, session token, or ingest key.

## Admin Surface (unchanged)

- `AdminBearerAuthMiddleware` and `VOCKY_ADMIN_AUTH_TOKEN` are untouched by the accounts work; `/admin/api/*` keeps its own separate bearer boundary. Reshaping the operator surface is P4.
