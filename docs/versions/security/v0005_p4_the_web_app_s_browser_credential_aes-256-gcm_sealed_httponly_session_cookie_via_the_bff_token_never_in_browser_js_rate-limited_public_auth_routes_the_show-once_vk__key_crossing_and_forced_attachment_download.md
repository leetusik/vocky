---
doc_id: security
version: v0005
created_at: 2026-07-16T23:31:28+09:00
source: P4.REVIEW
summary: P4: the web app's browser credential — AES-256-GCM sealed httpOnly session cookie via the BFF (token never in browser JS), rate-limited public auth routes, the show-once vk_ key crossing, and forced attachment download
previous: v0004_p7_mcp_requires_a_per-project_vk__credential_same_guard_401_last_used_at_as_api_dns-rebinding_on_static_token_retired
---

# Security

## Status

Covers the authentication and secret-handling posture landed in P2 (password hashing, account session tokens, per-project ingest credentials, the mandatory `/api/*` ingest boundary) plus the P3 authorization posture for the new feedback surfaces: project-scoped read/manage authorization that answers 404-never-403 on cross-project/cross-tenant ids, the single-key project read/manage surface, best-effort `last_used_at` stamping, and the tightened project-scoped self-read. As of **P7** it also covers the MCP capture endpoint: `/mcp` is guarded by the same mandatory per-project `vk_` credential auth as `/api/*`, and its Streamable-HTTP transport carries DNS-rebinding protection. As of **P4** it also covers the **browser** — the web app in `web/` introduced vocky's first browser-held credential (a sealed httpOnly session cookie), its first public rate-limited auth surface, and the first place a plaintext `vk_` key is displayed to a human. Attachment-download authorization and admin-token handling are covered in `architecture.md` / `api.md`.

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

## The Web App's Browser Credential (P4)

The `web/` app is the first place a vocky credential lives **in a browser**. Its whole security posture follows from one decision (D-P4-2): the browser talks only to the Next.js origin, and the Next.js server talks to vocky server-to-server.

- **The vocky session token never reaches browser JS.** It is sealed into an httpOnly cookie the Next app sets for itself, and the server unseals it per request to inject the `Authorization: Bearer`. There is no token in `localStorage`, no token in a JS variable, and no token in rendered HTML — so an XSS on our origin cannot exfiltrate a 30-day session bearer. It also means **vocky needs no CORS**: no browser ever calls it directly.
- **Cookie sealing.** `vocky_session` = `v1.<iv>.<ct>.<tag>` (base64url parts), **AES-256-GCM**, key = `sha256(SESSION_SECRET)`, a **fresh random 12-byte IV per seal**, sealed plaintext JSON `{token, exp}`. GCM means the cookie is both encrypted and authenticated — a tampered IV, ciphertext, or tag fails the tag check.
- **The open path never throws and never partially trusts.** `openSession` returns the token or **`null` for every failure** — wrong shape/version, tag mismatch, bad JSON, expired `exp`, rotated or missing secret — so a caller cannot accidentally treat a damaged cookie as a valid one; all failures collapse to "no session".
- **Cookie attributes.** `httpOnly`, `SameSite=Strict`, `path=/`, `maxAge` 30d (deliberately matching vocky's own session TTL, so the cookie cannot outlive the token it carries), and `Secure` when `NODE_ENV === "production"`.
- **`SESSION_SECRET` is the key to every live session.** Rotating it invalidates all of them (every user must sign in again) — the intended behavior, and the emergency lever if it is ever exposed. It and `VOCKY_API_BASE_URL` are **server-only** (never `NEXT_PUBLIC_`, read behind `server-only`).
- **A crypto-valid cookie is not a live session.** The signed-out bounce **verifies against `/auth/me` before redirecting**, so a cookie whose vocky token was revoked out-of-band renders the login form instead of ping-ponging. Only a **401** logs you out; other errors (vocky down) are rethrown rather than silently treated as a logout.

## The Web App's Public Auth Surface (P4)

The BFF routes `POST /api/auth/{login,signup,logout}` are the app's only unauthenticated entry — the one place a caller has no session yet — and therefore its attack surface. All three run **one audited pipeline** (`src/lib/bff.ts`) rather than duplicated per-route copies:

```
JSON-only 415 → same-origin 403 → per-IP rate limit 429 → parse 400 / schema 422 → vocky → seal cookie 200
```

- **vocky's `detail` is never echoed.** The response body is only `{ok}`; the client keys off the status. Pass-through statuses are deliberately narrow (login `[401, 400]`, signup `[409, 400]`); anything else upstream → 502. This preserves the backend's **no-enumeration** property at the browser edge: a wrong password and an unknown email produce the same 401 with no distinguishing text.
- **Rate limits are per-IP and per-route-namespaced** (`auth-login:` / `auth-signup:` + IP): login **5/15min** (the stricter, because it is the guessable one), signup **10/15min**. The namespacing is a real control, not tidiness — a shared bare-IP bucket would let login attempts drain signup's budget (and vice versa).
- **Same-origin is enforced** on every credential POST (403 otherwise), and the session cookie is `SameSite=Strict`, so a cross-site page can neither drive these routes nor ride an existing session.
- **Logout never fails open**: it revokes at vocky best-effort and then **unconditionally** clears the cookie, so a vocky outage can never leave a signed-out user still holding a live session cookie.

## The Show-Once `vk_` Key in a Browser (P4)

Minting a project credential in the web app is the **only** place vocky displays a plaintext secret to a human, and the single deliberate exception to the app's "no vocky data crosses a client boundary" rule.

- The key crosses to the client in the **server action's state**, never in the server-rendered page tree. That placement is what makes it survive the post-mint revalidation yet **vanish on the next submit or navigation**. It is never logged, never placed in a URL, and never persisted anywhere in the web app.
- After any reload only the 12-character `token_prefix` stub remains — the backend keeps only `sha256_hex(key)`, so it is genuinely unrecoverable (see "Per-Project Ingest Credentials" above).
- Dismissal is keyed by the action state's `ok` stamp rather than a sticky boolean: a `dismissed` flag would silently swallow the *next* minted key — the one failure mode where a missed render is unrecoverable rather than merely annoying.

## Forced Attachment Download (P4)

The web app's attachment proxy (`/api/app/feedback/{id}/attachments/{id}`) exists because the browser holds no bearer, so bytes must be relayed server-side. It **forces `Content-Disposition: attachment`** — this is a security control, not a UX preference:

- The bytes **and their declared content type** are uploader-supplied. `X-Content-Type-Options: nosniff` does not save you here, because the danger is not MIME **sniffing** — it is the declared type being *honestly* `text/html`. Serving that inline from our own origin is **stored XSS against our own session cookie**.
- Forcing the download makes the content type irrelevant to safety. The proxy also sends `nosniff` and `cache-control: private, no-store` (a per-user private response must never land in a shared cache), and maps vocky's 401 → 401, 404 → 404, malformed ids → 400, everything unexpected → 500.

## Backend Authorization Preserved at the Web Surface (P4)

The web app enforces **no** authorization of its own — it is a renderer of the backend's stance, which is the point: there is no second, weaker copy of the rules to drift.

- **404-never-403** survives end-to-end: the app maps vocky's `404` **and** `400` → its own not-found page. Collapsing the two is deliberate — a malformed id is effectively not-found, and distinguishing "malformed" from "not yours" leaks the shape of what exists.
- Legacy NULL-`project_id` feedback rows stay invisible in the app because `/app/feedback` already scopes them out; the app adds no path around that scope.
- The app renders no vocky token, `vk_` key, or cookie value into any page, on any route.

## Admin Surface (unchanged)

- `AdminBearerAuthMiddleware` and `VOCKY_ADMIN_AUTH_TOKEN` are untouched by the accounts work; `/admin/api/*` keeps its own separate bearer boundary. **P4 resolved the operator-surface reshaping by replacement**: the `web/` app is the new browser surface, and the packaged Admin Web UI is superseded but still mounted (its packaged docs still reference the retired static `VOCKY_API_AUTH_TOKEN` and are not current guidance). Physical removal of that UI is **P6**; until then, a deployment exposing `/admin` should still set `VOCKY_ADMIN_AUTH_TOKEN`.
