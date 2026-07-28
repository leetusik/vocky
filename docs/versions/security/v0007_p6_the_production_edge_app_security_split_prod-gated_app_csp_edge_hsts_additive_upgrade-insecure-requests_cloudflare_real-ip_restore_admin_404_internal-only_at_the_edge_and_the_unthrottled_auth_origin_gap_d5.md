---
doc_id: security
version: v0007
created_at: 2026-07-28T16:33:19+09:00
source: P6.REVIEW
summary: P6: the production edge/app security split — prod-gated app CSP, edge HSTS + additive upgrade-insecure-requests, Cloudflare real-IP restore, /admin 404 internal-only at the edge, and the unthrottled /auth/* origin gap (D5)
previous: v0006_p5_the_cli_s_on-disk_30-day_session_token_at_.config_vocky_config.json_0600_the_first_filesystem-resident_vocky_session_credential_the_cli_holds_the_session_token_and_mints_vk__keys_for_api
---

# Security

## Status

Covers the authentication and secret-handling posture landed in P2 (password hashing, account session tokens, per-project ingest credentials, the mandatory `/api/*` ingest boundary) plus the P3 authorization posture for the new feedback surfaces: project-scoped read/manage authorization that answers 404-never-403 on cross-project/cross-tenant ids, the single-key project read/manage surface, best-effort `last_used_at` stamping, and the tightened project-scoped self-read. As of **P7** it also covers the MCP capture endpoint: `/mcp` is guarded by the same mandatory per-project `vk_` credential auth as `/api/*`, and its Streamable-HTTP transport carries DNS-rebinding protection. As of **P4** it also covers the **browser** — the web app in `web/` introduced vocky's first browser-held credential (a sealed httpOnly session cookie), its first public rate-limited auth surface, and the first place a plaintext `vk_` key is displayed to a human. As of **P5** it also covers the **`vocky` CLI**, which introduced vocky's first credential resident on the local **filesystem** — a 30-day session token written `0600` under `~/.config/vocky/` (see "The CLI's On-Disk Session Token" below). As of **P6** it also covers the **production browser-transport posture** — the app/edge Content-Security-Policy split, HSTS, Cloudflare real-IP restore, and the decision to keep `/admin` unreachable from the internet (see "Production Transport Security" below). Attachment-download authorization and admin-token handling are covered in `architecture.md` / `api.md`.

> **P6's production security posture is authored, not live.** The vhost, headers, and TLS choices below describe `deploy/vocky.conf` and `web/next.config.ts` as they sit in the repo. **Nothing is deployed** — `https://vocky.hi2vi.com` does not answer, and none of the edge-side controls has ever been exercised by a real request. The live bring-up is **P12**.

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

## The CLI's On-Disk Session Token (P5)

The `vocky` CLI is the **first place a vocky credential lives at rest on the local filesystem** (the web app's is a browser cookie; the service holds only hashes). The credential it stores is the account **session token** — the same opaque, 30-day, hashed-in-DB token minted by `/auth/*` (see "Session Tokens" above) — **not** a `vk_` ingest key.

- **On-disk location and permissions.** The token (plus an optional base URL) is written as JSON to `~/.config/vocky/config.json` — XDG-aware, overridable with `VOCKY_CONFIG_DIR`. The config **directory is created `0700`** and the **file `0600`** (created via `os.open(..., 0o600)` then `chmod`), so the token is owner-only readable and never world- or group-readable. No password is ever written to disk — only the post-auth session token.
- **The CLI holds the session token, not the `vk_` key.** Like the web app, the CLI authenticates to the `/app/*` control plane with the session token and **mints** `vk_` keys there; it never stores or uses a `vk_` key for `/api/*`. A freshly minted `vk_` key is shown **once** on stdout with an explicit non-recoverable warning and is never persisted by the CLI (the show-once discipline of "Per-Project Ingest Credentials" holds — the CLI keeps only what the user copies).
- **Logout clears it.** `vocky logout` best-effort revokes the session at `/auth/logout` (hard-revoking the DB token row) and then unconditionally clears the local token, so a signed-out CLI holds no live credential. An expired or revoked token surfaces the same generic "Not signed in — run `vocky login`." rather than distinguishing failure modes.
- **Headless-secret hygiene.** `signup`/`login` accept the password via `--password-stdin` (one line of stdin) so the password never lands on a process argv; `VOCKY_CONFIG_DIR` lets an agent scope a throwaway, isolated session per task rather than sharing the user's real store.

## Admin Surface — the Web UI is gone; the REST boundary remains (P6)

**The packaged same-origin Admin Web UI was physically removed in P6** (`src/vocky/admin_ui.py`, `src/vocky/admin_assets/*`, the `/admin` and `/admin/assets/*` routes, and the wheel asset-packaging check). P4 had already superseded it with the `web/` app; P6 deleted it. Its stale packaged docs — which still described the retired static `VOCKY_API_AUTH_TOKEN` model — went with it, so that particular piece of misleading in-product guidance no longer exists anywhere.

What is **unchanged**: `AdminBearerAuthMiddleware`, `VOCKY_ADMIN_AUTH_TOKEN`, and the nine `/admin/api/*` endpoints. The Admin REST bearer boundary is exactly as it was; only the browser shell that consumed it is gone. After the removal, the **only** routes under the `/admin` prefix are `/admin/api/*` — there is no unauthenticated `/admin` shell left to load.

**`/admin` is internal-only in production, by edge policy.** `deploy/vocky.conf` answers `location /admin/ { return 404; }`, so `/admin/api/*` is not reachable through `https://vocky.hi2vi.com` at all — an operator uses it over the shared Docker network or an SSH tunnel. Two consequences worth stating plainly:

- The bearer token is **still required** on the api service, and `.env.prod.example` still lists `VOCKY_ADMIN_AUTH_TOKEN` as a box secret. That is deliberate defense in depth rather than redundancy: the edge is not the only thing that can reach `vocky-api:8000` — every co-tenant container on `changple_shared_network` can too, so the app-level bearer is the actual boundary and the edge 404 is a second, outer layer.
- Whether the token stays mandatory once `/admin` is edge-unreachable is a **P12** question, not settled here.

## Production Transport Security (P6) — the app/edge split

The browser-facing security headers are split deliberately across two owners. **The app owns the CSP; the edge owns HSTS and the TLS/real-IP layer.** nginx passes the app's headers through untouched — it must never re-declare or strip them.

### The app half — `web/next.config.ts`

The four generic headers (`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-Frame-Options: DENY`) ship on every path in every environment. `Permissions-Policy` was tightened to `camera=(), microphone=(), geolocation=(), browsing-topics=()`.

The **Content-Security-Policy is production-gated** (`process.env.NODE_ENV === "production"`), and is all-`'self'`:

```
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self';
frame-ancestors 'none'; base-uri 'self'; object-src 'none'
```

Three deliberate choices behind that string:

- **`'unsafe-inline'` on `script-src`/`style-src`, and no nonce.** Next's App Router emits nonce-less inline hydration/bootstrap scripts, `next/font` injects an inline `<style>`, and React emits inline `style` attributes. A nonce would require a `middleware.ts` that forces **dynamic rendering and loses static generation** across the app. The trade was taken knowingly; it is the same call the sibling `hi2vi_web` makes.
- **No external origin is allowed at all** — vocky's CSP carries none of hi2vi_web's analytics origins. Fonts are self-hosted (vendored Pretendard woff2), and the OG/apple-icon PNGs and the SVG favicon are same-origin server-rendered responses, so `img-src 'self' data:` and `font-src 'self'` cover everything the app actually loads. Introducing any third-party script, font, or image origin means editing this string.
- **`frame-ancestors 'none'`** duplicates `X-Frame-Options: DENY` on purpose (the modern directive plus the legacy header).

**The app sets no HSTS.** Under `pnpm dev` the CSP is absent by design, so local development is not fighting it.

### The edge half — `deploy/vocky.conf`

- **HSTS: `Strict-Transport-Security: max-age=300`, with no `includeSubDomains` and no `preload`.** The short max-age is the shared-edge house style: `hi2vi.com` hosts several co-tenant sites off one wildcard, and a long-lived or subdomain-wide HSTS pin taken by mistake is effectively irreversible for all of them. Lengthening it is a conscious later decision, not a default.
- **An *additive* `Content-Security-Policy: upgrade-insecure-requests`.** Multiple CSP headers **intersect** rather than override, so this composes with the app's policy instead of replacing it — that is why the edge may add this one directive and nothing else.
- **TLS** terminates on the wildcard `hi2vi.crt` (`*.hi2vi.com`), behind Cloudflare in **Full (Strict)** mode. `:80` returns a server-level `301` to https before any location matching.
- **Cloudflare real-IP restore** — the full v4+v6 `set_real_ip_from` range list plus `real_ip_header CF-Connecting-IP`. Without it every request would appear to originate from a Cloudflare edge address, which would break any IP-based logging or throttling and make abuse untraceable.
- `client_max_body_size 12m` bounds request bodies at the edge, ahead of the app's own attachment limits.

### The `/auth/*` origin rate-limit gap (D5)

**`/auth/login` and `/auth/signup` reach the api through the edge with no server-side per-IP limiter.** vocky's only rate limiting lives in the **web BFF** (`/api/auth/*`, 5/15min login and 10/15min signup, per-IP and per-route-namespaced) — that protects the browser path but **not** a direct HTTP client hitting `/auth/*`, which is an unauthenticated password grant plus open signup.

The obvious fix is unavailable at this edge: `limit_req_zone` names are **global across the whole `conf.d/` tree**, so declaring one would risk an `nginx -t` failure for every co-tenant site — a house-rule violation.

**Status: accepted for launch behind Cloudflare**, and tracked as deferred job **D5** — add a Cloudflare rate-limiting rule for `/auth/*` and/or an in-process per-IP limiter in `src/vocky/auth_api.py`. It is folded into the P12 bring-up. This is a known, deliberate gap, not an oversight.
