---
doc_id: security
version: v0009
created_at: 2026-08-04T12:50:15+09:00
source: P12.REVIEW
summary: P12: admin auth is fail-closed (503 when unconfigured), all three box secrets abort a blank deploy, and the /auth/* rate-limit gap is closed by an in-process limiter
previous: v0008_p10_org-level_vk__keys_are_a_real_trust-boundary_widening_key_scope_is_now_user-chosen_project-bound_or_org-level_and_the_guarantee_is_anchored_on_tenancy_plus_a_middleware-resolved_non-null_project-id_tuple
---

# Security

## Status

Covers the authentication and secret-handling posture landed in P2 (password hashing, account session tokens, per-project ingest credentials, the mandatory `/api/*` ingest boundary) plus the P3 authorization posture for the new feedback surfaces: read/manage authorization that answers 404-never-403 on out-of-scope ids, the single-key read/manage surface, best-effort `last_used_at` stamping, and the tightened self-read. As of **P7** it also covers the MCP capture endpoint: `/mcp` is guarded by the same mandatory `vk_` credential auth as `/api/*`, and its Streamable-HTTP transport carries DNS-rebinding protection. As of **P4** it also covers the **browser** — the web app in `web/` introduced vocky's first browser-held credential (a sealed httpOnly session cookie), its first public rate-limited auth surface, and the first place a plaintext `vk_` key is displayed to a human. As of **P5** it also covers the **`vocky` CLI**, which introduced vocky's first credential resident on the local **filesystem** — a 30-day session token written `0600` under `~/.config/vocky/` (see "The CLI's On-Disk Session Token" below). As of **P6** it also covers the **production browser-transport posture** — the app/edge Content-Security-Policy split, HSTS, Cloudflare real-IP restore, and the decision to keep `/admin` unreachable from the internet (see "Production Transport Security" below). As of **P10** it covers a **genuine widening of the ingest trust boundary**: a `vk_` key may now be minted at **org** level, spanning every project in its org (see "Ingest Key Scope" below — read that section before anything else in this doc). As of **P12** the posture is **live, not authored**, and two long-standing gaps are closed: `/admin/api/*` auth now **fails closed** and the public `/auth/*` surface has a real origin rate limit (see both sections below). Attachment-download authorization and admin-token handling are covered in `architecture.md` / `api.md`.

> **P6's production security posture is now live (P12, 2026-08-04).** The vhost, headers, and TLS choices below are serving real requests at `https://vocky.hi2vi.com`. Two structural changes came with the launch: the vhost's canonical home moved to the **`leetusik/edge` repo** (`edge/conf.d/vocky.conf`; this repo keeps `deploy/vocky.conf.md` as a pointer — the *behaviour* below is unchanged, only the file's location), and **P12 closed the two security gaps this doc previously recorded as accepted** — fail-open admin auth (P12.S1) and the missing `/auth/*` origin rate limit (P12.S3, deferred job **D5**, now resolved). Both sections below are rewritten accordingly.

## Ingest Key Scope — the P10 trust-boundary change (read this first)

**Before P10 a `vk_` ingest key was bound to exactly one project at both binding *and* enforcement, and this document published that as a schema-anchored guarantee.** The sentence it rested on was: *"Because `project_credentials.project_id` is `NOT NULL`, the forced filter can never degrade to an unscoped read."* **That statement is retired. It is no longer true of the schema, and it is no longer the mechanism that holds the boundary.** Migration `20260728_1200` made `project_credentials.project_id` nullable and added `project_credentials.tenant_id` (`NOT NULL`, FK `tenants` CASCADE).

This is **not** a wording update. It is a real widening: a credential now exists that reads, writes, and manages feedback across **many** projects. What replaces the old guarantee is two things, both verified in code, not aspirational:

**(a) Tenancy isolation is the outer boundary, and it is unconditional.** Every ingest credential carries a `tenant_id` that is always set, on **every** row including project-bound ones. No credential — of either scope — can reach data outside its own tenant. A key's scope is resolved from its own `tenant_id` / `project_id`, never from anything the caller sends: `POST /api/feedback` accepts an optional `project` **name**, but that name is only ever get-or-created **under the calling credential's own tenant** (`vocky.capture.resolve_capture_project`), so it cannot be used to reach or to create a project in someone else's org.

**(b) The key's *inner* scope is explicitly chosen by the user at mint time, and it is one of exactly two shapes.**

| scope | minted at | `project_id` | reaches |
|---|---|---|---|
| **project-bound** (the narrow default) | `POST /app/projects/{id}/credentials` | the project's id | exactly that one project |
| **org-level** (P10, opt-in) | `POST /app/credentials` | `NULL` | every project in its org, **including projects created later** |

A user must ask for the broad key; nothing upgrades a narrow key, and nothing silently mints a broad one. Which one a caller holds is reported by the credential payload's `project_id` — a UUID for project-bound, JSON `null` for org-level. **`project_id === null` is the org-key discriminator**; there is no separate scope field.

### The enforcement mechanism that replaces the `NOT NULL` argument

The old argument was *"the column cannot be NULL, therefore the filter cannot be absent."* The new argument is stronger, because it does not depend on the column at all:

- **The scope is resolved once, in the ingest middleware, into a `tuple[UUID, ...]` that is never `None`.** `ProjectCredentialAuthMiddleware` calls `resolve_credential_project_ids(credential)` and stashes the result on the ASGI scope under `vocky.credential_project_ids`; handlers read it back with `get_request_project_ids(request)`. A project-bound key resolves to `(credential.project_id,)` with **no** database call; an org-level key resolves to its tenant's project id set. Handlers do **not** derive a filter from `credential.project_id` — a repo-wide grep confirms zero filter sites do so, and the only three remaining reads of that attribute are the scope resolver itself, the capture resolver, and one *serializer-shape* fork (below).
- **An unscoped project read is no longer expressible in the type.** `FeedbackQueryFilters.project_id` — the single-project filter whose `None` meant *"no filter"* rather than *"no rows"*, and which was the actual mechanism behind an unscoped read — was **deleted** in P10. Project scoping is now only `project_ids`, a set.
- **An empty scope short-circuits to an empty result; a scope is never collapsed to `None`.** An org that owns no projects resolves to an empty tuple, and every consumer either returns an empty page / zeroed metrics explicitly or uses set membership (`record.project_id not in scope`, always false for an empty set → 404). A latent pre-existing fail-open on `/app/usage` — an empty project set collapsing via `project_ids or None` into *no project filter at all*, i.e. a global cross-tenant read — was found and **defused** in the same phase.
- **Scope resolution fails closed.** An `AccountsReadError` while resolving the scope answers `500 {"detail": "credential scope unavailable"}` and never falls through to a handler. This is deliberately *unlike* the neighbouring best-effort `last_used_at` stamp, which still swallows its failure; the two are not meant to be consistent.
- **Enqueue is the last enforcement point on the write path.** `resolve_capture_project` never returns `None`; the capture queue round-trips `project_id` nullably and the worker never re-derives it, so a write that got past enqueue with a project is correctly bound for the rest of its life.

### What did *not* change

- **Every pre-existing project-bound key behaves exactly as it did before.** This was proved rather than asserted: the enforcement rewrite landed **dark** (before any org key could be minted) and the entire existing suite passed **191/191 byte-for-byte with zero assertion edits**. That proof is only available before the mint surface exists and cannot be re-derived now; it is cited here as the additivity evidence.
- A project-bound key **ignores** the new `project` capture field entirely — not compared, not rejected, not 400'd. That is precisely what keeps existing clients unchanged.
- `/api/project/feedback` records still **omit** `project_id` for a project-bound caller (the premise "the project-scoped caller knows its own project from its credential" still holds). Only an **org-level** caller's records carry `project_id`, because for them that premise breaks. A client must key this off the credential's scope, not off one sample response.

### Deliberately not done: a distinct org-key prefix

Both scopes use the same `vk_` prefix. The prefix is **never validated** — auth resolves purely by `sha256_hex` — so a second prefix would buy no cheap pre-DB branch, and `vk_` is published as *the* key shape across the docs and the product. **The counter-argument is recorded honestly:** a distinct prefix would let a human, a log scrubber, or a secret-scanning rule tell a broad key from a narrow one at a glance, which has real incident-response value. Nothing forecloses it — it would be a mint-side-only, purely additive change, since nothing reads the prefix for auth.

### Blast radius, stated plainly

An org key is a bigger secret than a project key. Leaking one exposes **every project in the org**, present and future, for capture, read, **and** manage (including delete). Revoking one cuts every project at once. The product surfaces the distinction rather than hiding it: the dashboard shows org keys in their own panel, `vocky keys mint` prints the scope it just minted, and `vocky keys list` marks each row's scope.

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
- `require_user` resolves a token to the caller and their tenant; any miss (absent, malformed, unknown, expired, dangling user/tenant) raises `AuthError`, rendered as a generic `401` with `WWW-Authenticate: Bearer`. It picks `tenants[0]` (oldest-first) with no active-org selection — correct while a user has exactly one org, and precisely why multi-org membership stays deferred.
- **Signup's transactional gap is narrowed, not closed (stated so it is not mistaken for fixed).** P10's `provision_signup` puts the org, the owner membership, and the `"default"` project in **one** session and one commit, but `create_user` still commits ahead of it. A failure between the two therefore still leaves an org-less user who can never authenticate — fewer partial states than before, but not zero. `signup`'s own docstring says so.

## Ingest Credentials (project-bound and org-level)

- A key is minted as `key = "vk_" + generate_opaque_token()`, at either scope. The plaintext is returned **once** — in the `POST /app/projects/{id}/credentials` response (project-bound) or the `POST /app/credentials` response (org-level, P10) — and is never recoverable afterward.
- Only `sha256_hex(key)` (`token_hash`, UNIQUE) and a short display `token_prefix = key[:12]` are stored. Credential records and list responses expose `token_prefix` but **never** `token_hash` or the raw key. This is identical at both scopes; the payload shape is byte-identical and differs only in `project_id` being a UUID vs `null`.
- Revocation is a soft-revoke at either scope: `DELETE …/credentials/{id}` sets `revoked_at`. The ingest lookup (`get_active_credential_by_token_hash`) filters `revoked_at IS NULL`, so a revoked key of either scope fails `/api/*` auth immediately.
- **The two management surfaces are mutually disjoint, in both directions.** `GET /app/credentials` lists only `project_id IS NULL` rows; `GET /app/projects/{id}/credentials` lists only that project's rows. A tenant's keys therefore enumerate exactly once across the two, and neither surface can revoke or probe the other's rows — see "Tenant Isolation" for the 404 rule that enforces it.

## Mandatory `/api/*` and `/mcp` Ingest Auth

- Public REST ingestion is **strictly mandatory** credential auth. `ProjectCredentialAuthMiddleware` guards every `/api/*` HTTP request: it extracts the bearer, hashes it, and requires an active (non-revoked) project credential to match. There is **no** token argument and **no** open/unauthenticated fallback — the previous optional static-token model (`VOCKY_API_AUTH_TOKEN`) is retired.
- As of **P7** the same guard also covers the **entire `/mcp` MCP endpoint** (the middleware predicate is `is_api_path(p) or is_mcp_path(p)`, where `is_mcp_path` matches `/mcp` and `/mcp/…`). The MCP `initialize` handshake is included, so an unauthenticated agent cannot even open a session; identical resolution, `401`, scope stash, and `last_used_at` stamp as `/api/*`. The retired **static `VOCKY_MCP_AUTH_TOKEN`** is **not** revived — MCP auth is now per-project `vk_` credentials.
- Missing, malformed, unknown, and revoked credentials **all** answer an identical generic `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`, so a caller cannot distinguish "no key" from "wrong key" from "revoked key".
- As of P3 the guard also **threads project scope**: on a successful auth it stashes the resolved `ProjectCredentialRecord` on the ASGI scope under the namespaced key `vocky.project_credential` (read by handlers via `get_request_credential`), and best-effort stamps the credential's `last_used_at` (see below). The namespaced scope key (not `request.state`) is deliberate — it survives any Starlette `scope["state"]` re-init inside the middleware stack, and it also survives crossing into the mounted FastMCP sub-app so an MCP tool can read the credential back off `ctx.request_context.request`.
- As of **P10** the guard resolves the credential's **project scope** in the same place and stashes it under a second namespaced key, `vocky.credential_project_ids` (read by handlers via `get_request_project_ids`, always a `tuple[UUID, ...]`, never `None`). Resolving it once, in one place, rather than per handler is the whole safety argument: there are ten credential-scoped call sites across four modules, and a single missed one would be a silent cross-tenant read rather than an error. Unlike the best-effort `last_used_at` stamp, a **scope-resolution failure fails closed** with a `500`. `credential.project_id` is not a filter and must never be used as one — see "Ingest Key Scope" above.

## MCP Endpoint Transport Security (P7)

- The `/mcp` FastMCP Streamable-HTTP transport enables **DNS-rebinding protection** by default: a strict `Host`/`Origin` allowlist (localhost — `127.0.0.1:*`, `localhost:*`, `[::1]:*` — always allowed, extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`). A publicly-exposed `/mcp` must add its public `Host` (with port) to the allowlist or the transport rejects the request. This is defense against a browser being tricked into posting to a local MCP server; it is orthogonal to the credential auth above (which is the actual access boundary).

## Scoped Read/Manage Authorization (P3, rescoped by P10)

P3 added project-scoped feedback surfaces; all of them enforce authorization in the handler and answer **404 (never 403)** on any id outside the caller's scope, so cross-project/cross-tenant existence is never leaked (the same stance as D-P2-5). **P10 replaced every single-project equality check on these surfaces with set membership against the middleware-resolved scope** — one element for a project-bound key, the org's project set for an org key. The 404-never-403 stance is unchanged; only the definition of "in scope" widened, and only for a key the user explicitly minted as broad.

- **`/api/project/feedback` (credential authed).** The authorized project set comes from the credential the ingest middleware resolved — never a path or query parameter, and never re-derived from `credential.project_id`. The list endpoint **forces** `filters.project_ids = get_request_project_ids(request)`, overriding any caller-supplied value, and returns an **empty page** rather than an unfiltered read when that set is empty. Every per-feedback op (`get` / `patch` / `delete` / `comments` / `attachment`) loads through `_load_project_feedback`, which returns the record only when `record.project_id` is **in** the scope, else `None` → 404; for mutating ops the ownership check runs **before** the mutation or any attachment-linkage read. Set membership also excludes legacy NULL-`project_id` feedback rows for free (`None not in (...)` is always true) — which matters more now than it did, because an equality check against a NULL-project *credential* would have **matched** those rows.
- **`/app/feedback` (session authed, cross-project).** Every handler resolves the caller's project set via `list_projects_for_tenant(ctx.tenant.id)` and scopes reads to it; any feedback outside that set (including legacy NULL-project rows) answers 404 via `_load_scoped_feedback`. Optional `?project_id` narrowing validates membership: malformed → 400, not-owned/unknown → 404. The list normalizer (`normalize_list_query`) does not read `project_id`/`project_ids`/`search` from the query string, so a caller cannot inject a project filter to escape their tenant scope — the handler sets the scope authoritatively. This surface was already set-based and is the pattern the P10 rewrite copied.
- **Tightened self-read (D-P3-6).** `GET /api/feedback` (end-user self-read, scoped by required `user_id` + `source_product`) additionally scopes to the authenticating credential's project **set** as defense in depth, so a product key cannot surface another project's rows even under a colliding `(user_id, source_product)`. For a project-bound key a one-element `IN` is equivalent to the old equality, NULL-row exclusion included; for an org key it is the org's project set, and an empty set short-circuits to an empty page. Its sibling attachment download (`GET /api/feedback/{id}/attachments/{id}`) remains scoped by `user_id` + `source_product` only and additionally requires the exact feedback + attachment UUIDs; extending project scope to it is a possible future hardening.

## Single-Key Read/Manage Surface (P3, D-P3-2; widened by P10)

- One `vk_` credential does **everything for its scope**: capture **and** scoped read + manage on `/api/project/feedback`. There are **no per-credential permission scopes** in the MVP — the authorization boundary is the credential's *project set*, not a per-key permission set. A future least-privilege split would add permissions without changing that boundary.
- **P10 made the boundary a user-chosen one project vs the whole org**, not a per-key permission grant. Both scopes still carry the same all-verbs authority within their set; there is still no read-only key, and an org key can delete feedback in any of its org's projects. That combination — broad scope *and* full verbs — is the reason the org key is documented as the bigger secret.

## Best-Effort `last_used_at` Stamping (P3)

- On each successful `/api/*` **or `/mcp`** ingest auth, `ProjectCredentialAuthMiddleware` stamps the credential's `last_used_at`; on each authenticated `/auth/*`/`/app/*` call, `require_user` stamps the auth token's `last_used_at`. Both are one indexed `UPDATE` by PK.
- Both stamps are wrapped in `try/except AccountsPersistenceError` → log and continue, so a stamping failure **never** turns an otherwise-valid ingest or authenticated request into a 500. There is no throttle (stamp-always); a throttle is a possible future optimization if the write becomes hot. The usage endpoints surface these values (operational visibility only — see D-P3-5, no metering/billing).

## Tenant Isolation

- The `/app/*` control-plane is tenant-scoped. Every per-project read/mutation resolves the project against `ctx.tenant.id` first and answers **404 (never 403)** when the project is missing or belongs to another tenant, so cross-tenant existence is never leaked. Credential endpoints apply the same rule before any credential work, and credential ids are checked against the scoped project's own list before revoke.
- **The org credential surface (P10) applies 404-never-403 more narrowly than tenancy alone, and that is deliberate.** `DELETE /app/credentials/{id}` answers `404 {"detail": "credential not found"}` unless the row is **both** `tenant_id == ctx.tenant.id` **and** `project_id IS NULL`. So a **project-bound credential of the caller's own tenant 404s here** — byte-identically to another tenant's key and to an id that does not exist. The org surface can therefore neither revoke nor *probe* a project-bound key; `/app/projects/{id}/credentials/{cid}` remains the only way to revoke one. A malformed UUID answers `400` (a shape error, not an existence signal).
- Ingest project **creation** is tenant-bound too: the `project` name an org key may send with a capture is get-or-created strictly under that credential's own `tenant_id`, is length-capped, and normalizes blank/whitespace-only input to the `"default"` project rather than creating one named `"  "`. A caller-supplied name can therefore never reach, name-collide with, or create a project in another org.

## Secret-Exposure Discipline

- Response serializers never emit secrets: `serialize_user` omits `password_hash`; `serialize_tenant`/`serialize_project` carry no secret; `serialize_credential` omits `token_hash` and the raw key; token/credential records carry only `token_prefix`. `serialize_credential` is **NULL-safe** as of P10 (`str(x) if x is not None else None`) — an org-level row renders `project_id` as JSON `null`, not the literal string `"None"`; it is shared with both usage surfaces, so the fix covers all of them.
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

## The Show-Once `vk_` Key in a Browser (P4, extended by P10)

Minting a credential in the web app is the **only** place vocky displays a plaintext secret to a human, and the single deliberate exception to the app's "no vocky data crosses a client boundary" rule. As of **P10** there are two such places — the project-detail page's mint form and the dashboard's org-keys panel — and they share **one** component (`web/src/components/show-once-key.tsx`) rather than two copies, so the discipline below is enforced in a single implementation. The org-key panel is the higher-stakes of the two: the secret it reveals spans the whole org.

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
- **The CLI holds the session token, not the `vk_` key.** Like the web app, the CLI authenticates to the `/app/*` control plane with the session token and **mints** `vk_` keys there; it never stores or uses a `vk_` key for `/api/*`. A freshly minted `vk_` key is shown **once** on stdout with an explicit non-recoverable warning and is never persisted by the CLI (the show-once discipline of "Ingest Credentials" holds — the CLI keeps only what the user copies).
- **P10 relaxed `--project` from required to optional on `vocky keys mint|list|revoke`, and the security cost is real and accepted.** Omitting `--project` now mints an **org** key instead of failing with Typer's exit-2 "missing required option". A script that relied on that failure to catch a forgotten `--project` now silently succeeds — with a *broader* key. The mitigation is announcement, not prevention: `keys mint` prints the scope it just minted (derived from which route the CLI itself called, not from the server's echoed `project_id`), and `keys list` marks each row's scope. This is a deliberate trade for CLI/dashboard parity, recorded rather than softened.
- **Logout clears it.** `vocky logout` best-effort revokes the session at `/auth/logout` (hard-revoking the DB token row) and then unconditionally clears the local token, so a signed-out CLI holds no live credential. An expired or revoked token surfaces the same generic "Not signed in — run `vocky login`." rather than distinguishing failure modes.
- **Headless-secret hygiene.** `signup`/`login` accept the password via `--password-stdin` (one line of stdin) so the password never lands on a process argv; `VOCKY_CONFIG_DIR` lets an agent scope a throwaway, isolated session per task rather than sharing the user's real store.

## Admin Surface — the Web UI is gone; the REST boundary remains (P6)

**The packaged same-origin Admin Web UI was physically removed in P6** (`src/vocky/admin_ui.py`, `src/vocky/admin_assets/*`, the `/admin` and `/admin/assets/*` routes, and the wheel asset-packaging check). P4 had already superseded it with the `web/` app; P6 deleted it. Its stale packaged docs — which still described the retired static `VOCKY_API_AUTH_TOKEN` model — went with it, so that particular piece of misleading in-product guidance no longer exists anywhere.

What is **unchanged**: `AdminBearerAuthMiddleware`, `VOCKY_ADMIN_AUTH_TOKEN`, and the nine `/admin/api/*` endpoints. The Admin REST bearer boundary is exactly as it was; only the browser shell that consumed it is gone. After the removal, the **only** routes under the `/admin` prefix are `/admin/api/*` — there is no unauthenticated `/admin` shell left to load.

**`/admin` is internal-only in production, by edge policy.** The vhost (`edge/conf.d/vocky.conf`, in the edge repo) answers `location /admin/ { return 404; }`, so `/admin/api/*` is not reachable through `https://vocky.hi2vi.com` at all — an operator uses it over the shared Docker network or an SSH tunnel. Two consequences worth stating plainly:

- The bearer token is **still required** on the api service, and `.env.prod.example` still lists `VOCKY_ADMIN_AUTH_TOKEN` as a box secret. That is deliberate defense in depth rather than redundancy: the edge is not the only thing that can reach `vocky-api:8000` — every co-tenant container on `changple_shared_network` can too, so the app-level bearer is the actual boundary and the edge 404 is a second, outer layer.
- **The fate question is settled (P12.S1): KEEP, FAIL CLOSED.** The nine routes stay, nothing was deleted, and `VOCKY_ADMIN_AUTH_TOKEN` remains a **mandatory** box secret.

### The defense-in-depth claim is true in code only since P12.S1

**It previously rested on a token that was optional.** `AdminBearerAuthMiddleware` guarded `/admin/api/*` **only `if self.token`**, and `config.py` defaults `VOCKY_ADMIN_AUTH_TOKEN` to `""`. Compose interpolated it as a plain `${VOCKY_ADMIN_AUTH_TOKEN}`, which substitutes an **empty string with a warning** for an unset variable rather than failing. A missing or typo'd `.env` line therefore yielded **nine unauthenticated `/admin/api/*` routes — including `PATCH` and `DELETE` on any feedback record — reachable by every co-tenant container on the shared network.** The edge 404 kept it off the internet; nothing kept it off the shared network. That is the exact shape of an "inner layer" that silently is not there.

Both halves are fixed:

- **The middleware fails closed.** With no token configured, **every** `/admin/api/*` request is refused with **`503`** and `{"detail": "Admin API is not configured"}` — deliberately *not* a `401` with a `WWW-Authenticate: Bearer` challenge, because there is no credential that could succeed. Once a token *is* configured, the pre-existing `401` + `WWW-Authenticate: Bearer` behaviour is unchanged.
- **All three box secrets abort the deploy when blank.** `compose.prod.yml` now uses `${VAR:?message}` at every interpolation site for `POSTGRES_PASSWORD` (three sites), `SESSION_SECRET`, and `VOCKY_ADMIN_AUTH_TOKEN`. This also closed a quieter hole: a blank `SESSION_SECRET` used to pass `deploy.sh`'s health gate completely — the web healthcheck fetches `/`, the static landing, which never reads it — and failed only when a real user tried to log in. (Testing this needs an explicit `--env-file`; `env -u VAR` false-passes because Compose auto-reads the project `.env`. See `operations.md`.)

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

### The edge half — `edge/conf.d/vocky.conf` (in the `leetusik/edge` repo)

- **HSTS: `Strict-Transport-Security: max-age=300`, with no `includeSubDomains` and no `preload`.** The short max-age is the shared-edge house style: `hi2vi.com` hosts several co-tenant sites off one wildcard, and a long-lived or subdomain-wide HSTS pin taken by mistake is effectively irreversible for all of them. Lengthening it is a conscious later decision, not a default.
- **An *additive* `Content-Security-Policy: upgrade-insecure-requests`.** Multiple CSP headers **intersect** rather than override, so this composes with the app's policy instead of replacing it — that is why the edge may add this one directive and nothing else.
- **TLS** terminates on the wildcard `hi2vi.crt` (`*.hi2vi.com`), behind Cloudflare in **Full (Strict)** mode. `:80` returns a server-level `301` to https before any location matching.
- **Cloudflare real-IP restore** — the full v4+v6 `set_real_ip_from` range list plus `real_ip_header CF-Connecting-IP`. Without it every request would appear to originate from a Cloudflare edge address, which would break any IP-based logging or throttling and make abuse untraceable.
- `client_max_body_size 12m` bounds request bodies at the edge, ahead of the app's own attachment limits.

### The `/auth/*` origin rate limit — gap closed (D5, P12.S3)

**Previously:** `/auth/login` and `/auth/signup` reached the api through the edge with **no** server-side per-IP limiter. vocky's only rate limiting lived in the **web BFF** (`/api/auth/*`, 5/15min login and 10/15min signup, per-IP and per-route-namespaced), which protects the browser path but **not** a direct HTTP client hitting `/auth/*` — an unauthenticated password grant plus open signup. It was accepted "for launch behind Cloudflare" and tracked as **D5**.

**Now:** an **in-process per-`(client IP, route)` fixed-window limiter** in `src/vocky/rate_limit.py`, wired into `signup` and `login` as the **first statement in each handler** — before body parsing and before any database or password work. `logout` and `me` are untouched: only the two unauthenticated routes are in scope. Defaults **20 requests / 900 s**, tunable via `VOCKY_AUTH_RATE_LIMIT` / `VOCKY_AUTH_RATE_WINDOW_S` (`<= 0` disables). A throttled call returns **`429`** with `{"detail": "too many requests — please retry later"}` and a `Retry-After` header; no `X-RateLimit-*` headers, keeping the response surface minimal.

The nginx option remains unavailable and is not a regression to revisit: `limit_req_zone` names are **global across the whole `conf.d/` tree**, so declaring one risks an `nginx -t` failure for **every** co-tenant site.

Four security properties worth keeping in mind before changing anything here:

- **Client IP precedence is `X-Real-IP` → first `X-Forwarded-For` segment → `request.client.host` → `"unknown"`.** This is load-bearing, not cosmetic: behind Cloudflare plus the shared edge, the socket peer is the **edge container**, so a naive peer-address limiter would put the entire internet in one bucket and throttle all users as a single client. The edge restores the real Cloudflare IP and forwards it at the server level. The flip side is that these headers are **client-controllable when a request does not arrive through the edge** — the limiter is an anti-abuse speed bump, not an authentication boundary, and must never be treated as one.
- **Keyed on IP and route only — never on the email.** `login`'s generic 401 (which does not distinguish unknown-email from wrong-password) therefore stays byte-identical, and the 429 check runs before any credential work, so the limiter leaks no account-existence signal.
- **It is per-process memory.** State is a module-global dict with a `20_000`-key prune cap (expired entries first, then the oldest half — worst case it *under*-counts, never over-counts). It resets on restart, and its correctness depends on `vocky-api` staying a **single uvicorn worker**: adding `workers=N` would silently divide the effective limit. That invariant is documented in the module docstring and beside `uvicorn.run(...)` in `src/vocky/main.py`.
- **A Cloudflare rate-limiting rule remains available as an outer layer**, at operator discretion. It was deliberately not made the primary mechanism: it is console-only, unversioned, and invisible to the test suite, whereas the in-process limiter is versioned, reviewable, and covered by tests — including one that proves two clients sharing a fixed ASGI peer address land in different buckets once one sends `X-Real-IP`, i.e. the exact trap above.

**Known follow-up, deliberately out of scope:** the BFF's separate, weaker JS limiter (`web/src/lib/rate-limit.ts`, 5/15min and 10/15min) is not aligned with the origin limiter's 20/900s. Two independent limiters on two paths to the same endpoints is defensible, but it is not a designed pair.
