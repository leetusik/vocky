---
doc_id: decisions
version: v0005
created_at: 2026-07-16T23:28:21+09:00
source: P4.REVIEW
summary: P4 web-app decisions: app in a repo subdir web/, server-side BFF + sealed httpOnly cookie (no CORS, no web-side DB), port the design system and defer the heavy design gate to P6
previous: v0004_p7_mcp-revival_decisions_write-only_scope_broadened-middleware_auth_binding_thin_mcpcapturefeedbackinput_transport_security_on
---

# Decisions

## Status

Records the durable design decisions made in phases P2 (accounts, tenancy, projects core), P3 (feedback API v2, cross-project search, usage monitoring), P7 (agent-capture revival — the write-only MCP surface), and P4 (the authenticated web app). Each was operator-approved during decomposition and should not be re-litigated without a new decision superseding it.

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
- **Consequences:** There is no way to run `/api/*` unauthenticated or with a deployment-wide token; every integration must mint a project key first. The packaged Admin UI docs still reference the retired token; P4 superseded that surface with the `web/` app rather than updating it, so those stale docs are removed with the UI itself in **P6** (they are not current guidance in the meantime).

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

## D-P3-1 — Feedback gains a nullable project scope, stamped at capture

- **Decision:** `feedback_events` gains a nullable `project_id` FK → `projects.id` (`ON DELETE CASCADE`). Capture stamps it from the authenticating credential's project, and the ingest middleware threads the resolved project scope onto the ASGI scope. Legacy rows stay NULL (pre-MVP, no backfill).
- **Why:** Per-project scoping is the foundation for the project-scoped API, cross-project search, and usage monitoring; stamping at capture off the credential is the single authoritative source of a record's project. Nullable + no backfill keeps the migration cheap and pre-MVP-honest.
- **Consequences:** Every project-scoped read matches on a real `project_id`, so legacy NULL rows fall out of scoped reads (they are unreachable through the new surfaces). Threading the credential onto the ASGI scope (not `request.state`) is what lets handlers scope without path/query params.

## D-P3-2 — "Both, full" project-credential scope; no per-credential scopes

- **Decision:** A project credential authorizes **capture and** project-scoped **read + manage** of its own project's feedback on `/api/*` (the external-admin-panel path). There are **no per-credential scopes** in the MVP — one `vk_` key does everything for its project; scopes are deferred.
- **Why:** The operator intent is for an external service's own admin panel to consume feedback directly with the same key it captures with. Per-credential scoping adds surface the MVP does not need.
- **Consequences:** Any active `vk_` key can list/get/patch/delete/comment its project's feedback via `/api/project/feedback`. A future least-privilege split would add per-credential scopes without changing the project boundary.

## D-P3-3 — Cross-project read + search live on `/app/*`

- **Decision:** Cross-project feedback read + search live on the session-authed **`/app/*`** control-plane (`require_user`), scoped to the caller's tenant's projects. Consumed by the P4 dashboard and P5 CLI.
- **Why:** A signed-in human owns many projects and needs to read/search across all of them at once; that is a control-plane concern (session token) distinct from the single-project `vk_`-key data-plane. Management stays on the `/api/project/*` credential surface; `/app/*` feedback is read + search only.
- **Consequences:** `/app/feedback` aggregates across `list_projects_for_tenant`; records carry their `project_id` so the caller can tell them apart. Cross-tenant / not-owned ids answer 404 (see D-P3-4/D-P2-5 isolation stance).

## D-P3-4 — Korean/multilingual search: `pg_trgm` substring, never `to_tsvector('english')`

- **Decision (operator-stated constraint):** Feedback **may be Korean**. Do **NOT** use `to_tsvector('english', …)` — English stemming is wrong for Korean, and Korean particles/조사 defeat word-token matching. The chosen mechanism is a language-agnostic **case-insensitive substring (`ILIKE`) match** over the concatenated user-visible text columns, accelerated by a **`pg_trgm` trigram GIN index** over that same immutable expression. `pg_trgm` availability was **confirmed** on the target Postgres (extension v1.6, `CREATE EXTENSION` succeeds), so the constraint is met without an external search engine.
- **Why:** Trigram substring matching is language-agnostic: it matches Korean 조사-attached forms (`결제` ⊂ `결제를`) and English uniformly, with no text-search configuration. Substring (`icontains`, `autoescape=True`) is correct with or without the index; the GIN index only accelerates it.
- **Consequences:** The predicate expression and the index expression are kept byte-for-byte in lock-step (built once in `_feedback_search_target()`, mirrored in the migration DDL) so the planner uses the index; only immutable operators (`||`/`coalesce`) are used because `concat`/`concat_ws` are merely STABLE and cannot back an expression index. Search is a filter, newest-first — not relevance ranking.

## D-P3-5 — Usage = derived metrics + last-used, no new tables, no metering

- **Decision:** Usage monitoring is **derived** from existing feedback data — reuse `get_feedback_metrics` scoped per project/tenant through the shared read chokepoint — plus surfacing the already-wired credential/auth-token `last_used_at` stamps. **No new tables**, no request-count metering (honors D-P2-7 free/no-billing).
- **Why:** Operational visibility (capture volume, last-used) is achievable entirely from data already stored; request-count metering would imply a billing direction the SaaS explicitly does not take.
- **Consequences:** The usage endpoints add no schema, no new query, and no migration; they are pure reuse. `last_used_at` is stamped best-effort by the ingest middleware / `require_user` (D-P3-1 groundwork) and surfaced by the per-project usage views.

## D-P3-6 — Tightened self-read: `GET /api/feedback` also scopes to the credential's project

- **Decision:** The existing end-user self-read (`GET /api/feedback`, scoped by required `user_id` + `source_product`) is **additionally** scoped to the authenticating credential's project (defense in depth), now that `project_id` is threaded.
- **Why:** Before P3 the self-read authorized purely on caller-supplied `user_id` + `source_product`, which are not bound to the credential; adding the credential's project narrows the read so one product's key can never surface another project's rows even under a colliding `(user_id, source_product)`.
- **Consequences:** The self-read list matches on the credential's project, so legacy NULL-project rows fall out of it (acceptable pre-MVP). The sibling end-user attachment download (`GET /api/feedback/{id}/attachments/{id}`) remains scoped by `user_id` + `source_product` only (it is not part of the D-P3-6 list tightening and additionally requires knowing the exact feedback + attachment UUIDs); a future hardening slice could extend project scope to it.

## D-P7-1 — Revive MCP capture write-only; the three read tools stay retired

- **Decision:** Bring back the agent-decided feedback capture retired in P1, but **only the write path** — the single `capture_feedback` tool. The three retired MCP read/query tools (`list_feedback`, `summarize_feedback`, `list_liked_conversations`) stay retired; all reads remain REST-only. `mcp.list_tools()` returns exactly `["capture_feedback"]`.
- **Why:** The operator intent is specifically "only post — the agents linked to Vocky MCP save user feedback at their own judgement". Reads already have first-class scoped/authenticated REST + `/app` surfaces (P3), so reviving read tools would duplicate surface with weaker scoping.
- **Consequences:** MCP is a capture-only ingress feeding the shared queue/store; no read data ever leaves through MCP. A future read tool would be a new decision, not an implicit part of this revival.

## D-P7-2 — MCP auth binds via the broadened ingest middleware + ASGI-scope read (not a FastMCP TokenVerifier), and the static token stays retired

- **Decision:** Authenticate the **whole** `/mcp` endpoint by broadening the existing `ProjectCredentialAuthMiddleware` (predicate `is_api_path(p) or is_mcp_path(p)`) rather than adding a FastMCP-native bearer/`TokenVerifier` provider. The middleware runs before the `/mcp` `Mount` dispatches, stashes the resolved `ProjectCredentialRecord` on the ASGI scope, and the tool reads it back via `get_request_credential(ctx.request_context.request)` to stamp `project_id`. The static `VOCKY_MCP_AUTH_TOKEN` is **not** revived — MCP uses the same per-project `vk_` credentials as `/api/*`.
- **Why:** One auth path, one 401 shape, one `last_used_at` stamp for both ingress surfaces is simpler and less duplicative than a parallel FastMCP auth provider, and it guards the `initialize` handshake too (a FastMCP token verifier would only gate tool calls). It was empirically proven: an authed streamable-HTTP capture enqueues with the authenticating credential's `project_id`.
- **Consequences:** MCP capture is scoped to exactly one project (the credential's), with no project parameter in the tool schema. The credential propagates across the mounted sub-app boundary via the namespaced scope key, so no MCP-specific auth state is needed.

## D-P7-3 — Thin `McpCaptureFeedbackInput` (no `attachment_ids`), reusing the transport-neutral capture seam

- **Decision:** Revive a thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` (empty subclass) + a `normalize_mcp_payload` wrapper next to the REST ones, keeping `attachment_ids` **out** of the MCP tool schema. The tool builds this input, normalizes it, stamps `project_id`, and calls the same `enqueue_feedback` → worker → `feedback_events` pipeline as REST. No engine or schema change (`_normalize_capture_payload` reads `attachment_ids` via `getattr`, absent for MCP).
- **Why:** Agents have no upload flow, so exposing `attachment_ids` in the MCP schema would be dead surface. Reusing the transport-neutral seam keeps MCP and REST capture behaviorally identical downstream with no duplicated pipeline.
- **Consequences:** MCP capture aligns with the P3 v2 capture shape and stays attachment-free; the retired `CaptureFeedbackInput` alias was not revived (unneeded).

## D-P7-4 — MCP transport security (DNS-rebinding) on by default for a public `/mcp`

- **Decision:** Keep the FastMCP Streamable-HTTP transport's **DNS-rebinding protection on** with a localhost `Host`/`Origin` allowlist, extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`, rather than descoping it. (Auth is still the real access boundary — the per-project `vk_` credential.)
- **Why:** `/mcp` is intended to be publicly exposed (e.g. behind a Cloudflare Tunnel), where DNS-rebinding is a real browser-side risk; a minimal configurable allowlist is cheap and safe by default.
- **Consequences:** A public deployment must add its public `Host` (with port) to `VOCKY_MCP_ALLOWED_HOSTS`; the matcher requires a port, so a portless `Host` is rejected. Localhost always works without config.

## D-P4-1 — The web app lives in a repo subdirectory `web/`, not a separate repo

- **Decision:** The authenticated web app is a subdirectory **`web/`** of this repository, versioned and committed by the existing workflow engine alongside the backend. "hi2vi_web-style" (the operator's reference, `~/projects/personal/hi2vi_web`) means **stack, patterns, and the Claude design-gate workflow** — *not* repo topology: hi2vi_web is a separate repo we **template from**, never vendor or import.
- **Why:** One repo keeps the frontend and the API contract it consumes in the same review loop, the same slice workflow, and the same commit history — a contract change and its client move together. A second repo would buy independence the project does not need at pre-MVP and would cost cross-repo coordination on every `/app/*` change.
- **Consequences:** The frontend rides the backend's phase/slice process and doc set (`frontend.md` is part of this doc set). The same app will later carry the P6 landing page. The repo is now polyglot: Python (`uv`) for the service, TypeScript (`pnpm`) under `web/`, each with its own toolchain and gate.

## D-P4-2 — Browser↔API goes through a Next.js server-side BFF with a sealed httpOnly cookie

- **Decision:** The browser talks **only** to the Next.js origin; the Next.js server calls vocky server-to-server with `Authorization: Bearer`. The vocky session token is **sealed into an AES-256-GCM httpOnly cookie** (`vocky_session`) that the Next app sets for itself, never exposed to browser JS. **No CORS change to vocky, and no web-side database.**
- **Why:** The alternative — the browser calling vocky directly with a token in JS-reachable storage — would require opening CORS on vocky, and would put a 30-day session bearer where any XSS could read it. Sealing it in an httpOnly cookie means a script on our origin cannot exfiltrate the token, and keeping vocky same-origin-free means the API surface needs no browser-facing changes at all. A web-side DB would fork session state across two stores for no gain; the cookie *is* the state.
- **Consequences:** Two server-only env keys (`VOCKY_API_BASE_URL`, `SESSION_SECRET`); rotating `SESSION_SECRET` invalidates every live session. Authed mutations are **server actions** while the **public** auth surface (login/signup/logout) is BFF route handlers — the one place a caller has no session yet — and binary attachments need an explicit relay proxy because the browser holds no bearer. The cookie is `Secure` only in production, which makes plain-http local runs (`pnpm dev`) the supported way to drive an end-to-end check. The app is a stateless client; its only persistent state is the user's cookie.

## D-P4-3 — Port the design system and build functional pages; defer the heavy design gate to P6

- **Decision:** P4 **ports** hi2vi_web's Tailwind-v4 CSS-first `@theme` token system, `cn()`, and CVA primitives (adding a net-new `data-table`), and builds **functional** dashboard/project/feedback pages. It scaffolds `web/design/canvas/` plus the DesignSync/`SIGNOFF` convention but **defers the intensive operator design session to P6**, alongside the landing page. The brand palette is an explicit **neutral placeholder** (slate + one indigo accent) that keeps hi2vi's token *names*.
- **Why:** The dashboard's value is that it works — the design gate is a separate, operator-intensive activity that belongs with the landing page, where the brand is actually decided. Porting a proven token system now (rather than inventing one) keeps P4 focused on the auth/data surfaces, and doing it under hi2vi's token *names* means the later gate swaps **values only**, never call sites.
- **Consequences:** The app is visually provisional but structurally complete. Token names are load-bearing and must stay stable until P6; **no dark-mode toggle** exists (surfaces are explicit tokens, no `.dark` block). The `TrendChart` is a dependency-free inline SVG rather than a chart library — deliberately a P6 question. New components should not add palette tokens or CVA variants without a design reason.
