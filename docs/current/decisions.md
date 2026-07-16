---
doc_id: decisions
version: v0002
created_at: 2026-07-16T14:20:56+09:00
source: P2.REVIEW
summary: P2 auth-model and tenancy-shape decisions: email/password + opaque DB tokens, multi-tenant solo-owner, /app vs /api split, mandatory ingest auth
previous: v0001_bootstrap
---

# Decisions

## Status

Records the durable design decisions made in phase P2 (accounts, tenancy, projects core). Each was operator-approved during decomposition and should not be re-litigated without a new decision superseding it.

## D-P2-1 — Account auth: email + password + opaque DB-backed bearer tokens

- **Decision:** Real accounts use email + password. Passwords are hashed with argon2id. Login/signup mint a random opaque bearer token stored **hashed** (sha256, high-entropy, no pepper) in `auth_tokens` with a 30-day expiry. Logout deletes the row. **No JWT, no OAuth** in the MVP.
- **Why:** Opaque DB tokens are trivially revocable (delete the row) and carry no claims to keep in sync; they fit a self-contained service with a database already on the hot path. JWT/OAuth add key management and revocation complexity the MVP does not need. The web app (P4) and CLI (P5) will send the token as `Authorization: Bearer`.
- **Consequences:** Every authenticated request costs one indexed token lookup; there is no stateless verification. A future CLI device-flow onboarding (P5) builds on this token model.

## D-P2-2 — Tenancy: multi-tenant schema, solo-owner MVP flow

- **Decision:** Model tenancy fully (`users`, `tenants`, `tenant_members(role)`, `projects`, `project_credentials`) but ship a solo-owner flow: signup auto-creates one tenant with the user as the sole `owner` member. Invites, multiple members, and role management UI are deferred.
- **Why:** Getting the schema right up front (a membership join table with roles, ownership as a row rather than an `owner_id` column) avoids a painful migration later, while the solo-owner flow keeps the MVP surface small. `list_tenants_for_user` + "first tenant is active" is enough for now.
- **Consequences:** The data model already supports future multi-member tenants and roles; only the API/UX for them is missing.

## D-P2-3 — Control-plane vs data-plane split: `/app/*` vs `/api/*`

- **Decision:** Account/tenant/project/credential management lives on a session-token-authed **`/app/*`** control-plane (top-level prefix, guarded per-handler by `require_user`). Product feedback ingestion stays on the **`/api/*`** data-plane, authed by per-project credentials. Public account auth is a third surface, `/auth/*`. All three sit outside `/admin/api/*`.
- **Why:** The two planes have different callers (a signed-in human/agent managing an account vs a product backend sending feedback) and different credentials (session token vs project key). Separate prefixes let each middleware's path predicate cleanly include/exclude the right routes without entangling them.
- **Consequences:** `/auth/*` and `/app/*` bypass both bearer middlewares by construction; the `/api/*` guard never touches account routes.

## D-P2-4 — Strictly mandatory per-project ingest auth; static token retired

- **Decision:** `/api/*` auth is **mandatory** per-project credential auth with no open fallback. `ProjectCredentialAuthMiddleware` replaced the optional static-token `APIBearerAuthMiddleware`, and `VOCKY_API_AUTH_TOKEN` / the `api_auth_token` setting were removed. Missing/malformed/unknown/revoked keys all answer a generic 401.
- **Why:** A single shared global token is a weak, unrevocable-per-consumer boundary for a multi-tenant SaaS. Per-project keys are individually revocable, attributable to a project, and make "no unauthenticated ingest path" enforceable by construction.
- **Consequences:** There is no way to run `/api/*` unauthenticated or with a deployment-wide token; every integration must mint a project key first. The packaged Admin UI docs still reference the retired token and are deferred to P4.

## D-P2-5 — Cross-tenant isolation answers 404, never 403

- **Decision:** Any per-project read/mutation on `/app/*` answers **404** (not 403) when the project is missing or belongs to another tenant.
- **Why:** A 403 would confirm that a project id exists in another tenant. 404 makes cross-tenant existence indistinguishable from non-existence, closing an enumeration channel.
- **Consequences:** All `/app/*` per-project handlers resolve the tenant-scoped project first and treat "not mine" and "not found" identically.

## D-P2-6 — Capture-scoping boundary: identity only in P2

- **Decision:** P2 authenticates `/api/*` by project credential but does **not** attach the credential's project/tenant to `feedback_events` or reshape the capture payload. The ingest middleware is identity-only and does not stamp `last_used_at`.
- **Why:** Keeps P2 focused on identity/tenancy without touching the feedback schema and read model; per-project feedback scoping, search, and usage monitoring are a coherent unit of work for P3.
- **Consequences:** `feedback_events` has no `project_id` yet; credential `last_used_at` stays null. P3 owns threading project scope into capture.

## D-P2-7 — Free SaaS: no billing

- **Decision:** The SaaS is free — no paid plans, billing, usage metering, or plan tiers. No billing entities exist in the schema or code.
- **Why:** The pivot's goal is a usable free multi-tenant service; monetization is explicitly out of scope.
- **Consequences:** Accounts, tenants, projects, and credentials carry no plan/quota concept.
