---
doc_id: decisions
version: v0008
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: add D-P14-1, D-P14-2 and D-P14-3 for the agent-vs-human capture marker
previous: v0007_p10_add_d-p10-1..5_no_tenants-to-orgs_rename_a_default_project_but_a_friendly_org_name_one_vk__prefix_for_both_scopes_omitting_--project_mints_an_org_key_and_no_design_round_for_the_org-key_surface
---

# Decisions

## Status

Records the durable design decisions made in phases P2 (accounts, tenancy, projects core), P3 (feedback API v2, cross-project search, usage monitoring), P7 (agent-capture revival — the write-only MCP surface), P4 (the authenticated web app), P8 (the design gate — brand, app UI & landing), P10 (accounts v2 — orgs, org-level keys, default project), and P14 (public agent-recorded feedback — the agent-vs-human marker). Each was operator-approved during decomposition and should not be re-litigated without a new decision superseding it. **D-P8-1 supersedes D-P4-3** (the design gate D-P4-3 deferred is now held and closed). **D-P10-3 narrows D-P3-2** (a key's "both, full" authority now spans a *chosen* scope rather than always exactly one project). **P14 supersedes and narrows nothing** — but it re-raises D-P3-2 in a sharper setting, because unscoped `vk_` keys now live inside third-party agent runtimes (see `security.md`).

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

> **Superseded by D-P8-1.** The heavy design gate this decision deferred was moved out of P6 and **held and closed at P8** (the design; **P9** applies it). P6 is now production-deploy-only. The record below is unchanged as the P4-era decision; read D-P8-1 for the current position.

- **Decision:** P4 **ports** hi2vi_web's Tailwind-v4 CSS-first `@theme` token system, `cn()`, and CVA primitives (adding a net-new `data-table`), and builds **functional** dashboard/project/feedback pages. It scaffolds `web/design/canvas/` plus the DesignSync/`SIGNOFF` convention but **defers the intensive operator design session to P6**, alongside the landing page. The brand palette is an explicit **neutral placeholder** (slate + one indigo accent) that keeps hi2vi's token *names*.
- **Why:** The dashboard's value is that it works — the design gate is a separate, operator-intensive activity that belongs with the landing page, where the brand is actually decided. Porting a proven token system now (rather than inventing one) keeps P4 focused on the auth/data surfaces, and doing it under hi2vi's token *names* means the later gate swaps **values only**, never call sites.
- **Consequences:** The app is visually provisional but structurally complete. Token names are load-bearing and must stay stable until P6; **no dark-mode toggle** exists (surfaces are explicit tokens, no `.dark` block). The `TrendChart` is a dependency-free inline SVG rather than a chart library — deliberately a P6 question. New components should not add palette tokens or CVA variants without a design reason.

## D-P8-1 — The design gate D-P4-3 deferred is held and closed at P8; the landing design + build move to P8+P9 (supersedes D-P4-3)

- **Supersedes:** **D-P4-3**. The intensive operator design session D-P4-3 deferred to P6 was moved into this stream: **P8 runs the design gate** (Claude Design + operator; handoff → session → read-back → signed-off spec) and **P9 applies it**. P6 becomes production-deploy-only (its own folder is untouched per P8's constraint 7; the operator reconciles it at `P6.DECOMP`). **Not applied in code yet — that is P9.**
- **Decision (round 01 — the operator's rulings, concluded in the Claude Design session):** the durable record lives at `docs/reference/design/` (round 01 `output/{result.md, build-prompt.md}` + `SIGNOFF.md`); `build-prompt.md` is the implementation contract P9 sizes from. The resolutions:
  - **Brand:** vocky's own **deep-emerald** green on a green-cool neutral ramp — palette direction "B" (inherit hi2vi's *structure*, not its literal dark-forest+neon). Applied as a **names-kept value swap** (`--color-green #6366f1` placeholder → `#0C7A52`), which the one-swap-re-themes property (utilities compile to `var(--color-*)`) turns into a full re-theme without call-site churn. Token **renames deferred** (cost named; not this round).
  - **Type:** `--font-sans` → **Pretendard** (Korean-capable), `--font-mono` → **JetBrains Mono** (unchanged), `--font-en` retired to Pretendard; compact/data-dense scale. The one named non-trivial build cost is **Pretendard vendoring** (not on Google Fonts → `next/font/local`).
  - **Mode:** **light-only** (no `.dark` block); `on-primary` stays **white** (the deep-emerald passes AA with white text). `--breakpoint-xs` (zero consumers) dropped for a real `--breakpoint-app` (900px).
  - **New component vocabulary:** add `Select`, `Chip`/`Tag`, `Button` `destructive`/`destructiveOutline`; fold `LogoutButton` into `Button ghost`; split the overloaded `Badge archive` into rating (`liked`/`disliked`/`unrated`) + status (`active`/`revoked`); redesign `TrendChart` to a dependency-free area chart.
  - **Net-new surfaces:** the **public landing reclaiming `/`** (largest new build) and designed `loading`/`error`/`not-found`/`global-error` states.
  - **Backend/data contracts:** **no change required** (`build-prompt.md §9`) — everything maps to existing serializers; no `src/vocky/**` or P2/P3 contract reopening. Two web-tier-only behaviors: `/` gains a public landing behind the existing signed-in→dashboard bounce, and a project-detail breadcrumb from already-fetched data.
- **Why:** A big design change gets a design phase then an apply phase (P8 then P9); the phase's true size stays unknown until signoff, which is exactly why the apply is a separate phase whose `DECOMP` runs only after this gate closed. All brand decisions were concluded by the operator in the Claude Design session (zero brand decisions by Claude Code — the load-bearing constraint); Claude Code authored only the handoff.
- **Consequences:** P9 decomposes and sizes every apply slice from `build-prompt.md` (its executors have no DesignSync, so `build-prompt.md` is the complete on-disk source of truth; the 30-card set + `tokens.css` stay in the design project, not copied down). Until P9 lands, `frontend.md` still describes the live **placeholder** palette. D-P4-3's "until P6" / "a P6 question" clauses now read as **P8/P9** per this supersession.

## D-P10-1 — "Org" is product-facing naming only; the `tenants` table is not renamed

- **Decision:** P10 makes the accounts model explicitly **user → org → project**, but performs **no `tenants` → `orgs` rename**. The tenant row *is* the org. "Org" is adopted in web copy, CLI output, and docs; `tenant_id`, `tenants[]`, `VockyTenant`, `tenant_members`, and every route path stay exactly as they are.
- **Why:** The tenant id threads through the schema, the auth resolver, the whole `/app/*` surface, `feedback_events.project_id`'s owner chain, and the web BFF. A rename is a large mechanical diff with real regression risk and **zero behavior change** — a bad trade, and the same call the reference implementation made. Product-facing language is what users actually see, and that can move without touching a wire identifier.
- **Consequences:** `tenant` and `org` are synonyms in this codebase and the docs say so explicitly. Anyone reading the schema must translate; anyone writing user-facing text must say "org". A future rename remains possible but is its own mechanical slice, never folded into a feature phase.

## D-P10-2 — Signup provisions a `"default"` **project**; the org keeps its friendly auto-name

- **Decision:** Signup provisions the org, the owner membership, **and a project named `"default"`** in one transaction. **Only the project is named `"default"`.** The org keeps `"<email-local-part>'s workspace"`. There is deliberately **no `DEFAULT_ORG_NAME` constant**, and a test asserts its *absence*.
- **Why:** Before P10 a new account had zero projects and zero keys, so the product's own depicted flow began with manual setup — provisioning a project removes that. But adopting the reference implementation's literal `"default"` **org** name would buy nothing (nothing resolves an org by name) and would actively regress the app shell, which renders the org name to the user. This is a **recorded, deliberate divergence** from both the reference implementation and from an earlier phrasing of P10's own objective, which said signup provisions "a `default` org and a `default` project" — only the project half is true, and **the docs follow the code, not that sentence**.
- **Consequences:** `DEFAULT_PROJECT_NAME = "default"` is the only such constant. A later slice adopting a literal `"default"` org fails a test rather than drifting silently. Existing orgs are never renamed and acquire `"default"` lazily via get-or-create. Onboarding is documented as two steps, not three.

## D-P10-3 — Org-level keys are a real trust-boundary widening, landed additively and enforcement-first

- **Narrows:** **D-P3-2** ("both, full" project-credential scope). A `vk_` key still does capture **and** full read+manage with no per-credential permission scopes; what changed is that the *reach* is now a user-chosen scope — one project, or the whole org — rather than always exactly one project.
- **Decision:** `project_credentials.project_id` becomes **nullable**, where `IS NULL` means org-level, and `tenant_id` becomes `NOT NULL` at both scopes. A **nullable column, not a scope enum**. Critically, the phase was ordered so that **every credential-derived project filter became org-aware and set-based *before* any org key was mintable** — the enforcement slice landed **dark**, with no mint surface, and its acceptance criterion was that the entire existing suite passed **byte-for-byte with zero assertion edits** (191/191).
- **Why:** Unlike the reference implementation — where "org-level" was only a *wording* change, because its resolver already authorized by tenant — **vocky's keys were project-bound at both binding and enforcement**, and `security.md` published that as a guarantee. Relaxing the column without first rewriting enforcement would not have made org keys read *nothing*; a `None` single-project filter meant *"no filter"*, so a NULL-project credential would have **failed open to a global, cross-tenant read**. The ordering is therefore not a preference but the safety property, and the dark landing is the only moment at which additivity can be *proved* rather than asserted — a proof that disappears the instant minting is on.
- **Consequences:** Project scoping is expressible only as a set (`FeedbackQueryFilters.project_id` was deleted), a credential's scope is resolved once in the middleware into a tuple that can never be `None`, an empty scope short-circuits to an empty result and is never collapsed to `None`, and scope resolution fails **closed**. `security.md`'s schema-anchored guarantee is **retired and rewritten**, not reworded: the guarantee is now tenancy isolation plus an explicitly user-chosen key scope. An org key is a bigger secret — leaking it exposes every project in the org, present and future; revoking it cuts them all at once.

## D-P10-4 — One `vk_` prefix for both key scopes (counter-argument recorded)

- **Decision:** Org keys use the **same `vk_` prefix** as project keys. No distinct prefix. Scope is surfaced by `credential.project_id` (a UUID vs `null`) and by the product's own UI/CLI labelling.
- **Why:** The prefix is **never validated** — auth resolves purely by `sha256_hex` — so a second prefix buys **no** cheap pre-database branch, which was the only mechanical argument for one. `vk_` is published as *the* key shape across the docs and the landing page, and forking it mid-phase fragments that story for a distinction the product already surfaces explicitly.
- **Counter-argument, recorded honestly:** a distinct prefix would let a human, a log scrubber, or a secret-scanning rule tell a broad key from a narrow one **at a glance**, which has real incident-response value. Nothing here forecloses it: it would be a **mint-side-only, purely additive** change (nothing reads the prefix for auth), so only newly minted keys would carry it and every old key would keep working.
- **Consequences:** You cannot tell a key's blast radius by looking at it. Any tooling that needs to must read `project_id` from the credential payload, not parse the key.

## D-P10-5 — Omitting `--project` mints an **org** key; no design round for the org-key surface

- **Decision (CLI):** `vocky keys mint|list|revoke` relax `--project` from **required** to optional; omitting it selects the org-level route. The CLI derives the printed scope from *which route it called*, not from the server's echoed `project_id`.
- **Decision (design):** the org-key surface ships as a **panel on `/dashboard`** — no new route, no new nav entry — with **no Claude Design co-work round**. The phase decomposed in a single pass.
- **Why (CLI):** Org and project scope map 1:1 onto two route families, so one optional flag is the smallest honest surface; inventing a separate `--org` flag or a subcommand would encode the same bit twice. Deriving the scope line from the call site rather than the response sidesteps the absent-vs-`null` ambiguity entirely.
- **Why (design):** Design round 01 is closed and vocky already had every primitive the surface needs (`Card`, `DataTable`, `Badge`, the mint form, the show-once panel). The only open question was information architecture, and it has one honest answer: an org key belongs to no project, so it belongs on the org-level page.
- **Consequences (and the accepted cost):** `--project` **no longer has Typer's exit-2 "missing required option" path.** A script that relied on that failure to catch a forgotten `--project` now silently succeeds — **with a broader key than intended**. The mitigation is announcement, not prevention: `keys mint` always prints a `Scope:` line and `keys list` labels each row. This is recorded rather than softened; scripted minting should assert on the scope line. On the design side, the show-once key panel became a **shared component** rather than a second copy, and the org table deliberately keeps its own column set rather than being folded into a parameterized factory.

## D-P14-1 — The agent/human marker is a first-class `feedback_events.recorded_by` column, not a `trigger_type` value

- **Decision:** Persist *who recorded this feedback* as a **new nullable, indexed `recorded_by TEXT` column** on `feedback_events`, validated in the application against a **closed** two-value vocabulary — `agent`, `human` — with **`NULL` meaning *unspecified*** (every pre-P14 row, and any caller that does not state it). Validation mirrors `src/vocky/trigger.py`; there is no database `CHECK`. The column is **never backfilled and never inferred**, and it is **not** in the Admin or Project PATCH allowlist — it is capture-time provenance, not a review field. It never affects scoping or auth.
- **Why:** The operator asked for a *first-class* discriminator, and today the transport is not stored at all (`source.integration` is free-text convention only). A separate column is orthogonal to every existing dimension, indexable, filterable with the exact predicate pattern `_apply_filters` already uses, and extensible — a future `system` actor costs one constant and no migration.
- **The cheapest alternative, and why it was rejected.** Adding an `agent` value to **`trigger_type`** needed no migration at all: the index, the filters on four surfaces, and even the web dashboard's URL param already existed. It was a real contender. It was rejected because `trigger_type` answers **why capture happened** (`like`/`dislike`/`comment`/`rating`/`survey`/`manual`/`other`) while the marker answers **who recorded it** — orthogonal dimensions, and folding one into the other is lossy: an agent recording a survey response could then say `agent` **or** `survey`, never both. Overloading an existing enum is also the opposite of "first-class", and unwinding it later means a data migration over live rows.
- **Also rejected:** the `source.integration` convention (free text, no validation, no index — and the operator explicitly rejected convention-only); a boolean `is_agent` (cannot express "unspecified" without a third state anyway, and cannot grow a third actor kind); a key in `attributes` / `source_metadata` JSONB (not indexed, not filterable through the typed filter set, invisible to the dashboard).
- **Consequences:** Legacy rows are `NULL`, **not** `human` — so any dashboard split is **three-way** (agent / human / unspecified), and there is deliberately no filter value that selects only the `NULL` rows (a three-way split needs a new sentinel, not a filter tweak). The cost of the choice is breadth, not depth: the field threads mechanically through ~8 backend files plus the web types. A visible agent/human filter control in the dashboard was **explicitly not built** — that is product visual design and belongs to a design-bearing phase; P14 shipped the marker as a URL-driven filter and one detail-page row only.

## D-P14-2 — MCP capture defaults `recorded_by` to `"agent"`; REST defaults to `NULL`

- **Decision:** When the caller omits (or blanks) `recorded_by`, `normalize_mcp_payload` stamps **`"agent"`**; `normalize_rest_payload` leaves it **`None`**. An explicit caller value always wins on both transports. The transport-specific default lives **only** in `normalize_mcp_payload`; `_normalize_capture_payload` stays transport-neutral.
- **Why:** `/mcp` is by construction the agent-runtime surface — one write-only tool, documented as agent-decided capture (D-P7-1), and there is no human-driven MCP client. Defaulting it is therefore *correcting* the record rather than guessing, and it means the first third-party agent produces correctly-marked data even if it never learns the new argument. REST is genuinely mixed traffic (a product backend's UI events **and** the CLI/skill path an agent drives), so inferring `human` there would be wrong and inferring `agent` would be worse; `NULL` is the honest answer and keeps every existing REST client byte-for-byte unchanged.
- **Consequences:** Two transports carry different defaults for the same field — a deliberate asymmetry that must be documented wherever the field is, and it is (SKILL.md, README, `docs/cli.md`, `api.md`). The `vocky capture` CLI sends no marker at all and so always lands `NULL`; the public docs point at REST or `/mcp` when the marker matters rather than widening the CLI (see D-P14-3). Proven live end to end: MCP-omitted ⇒ `agent`, MCP-explicit `human` ⇒ `human`, REST-explicit ⇒ `human`, REST-omitted ⇒ `NULL`.

## D-P14-3 — Sentiment → `message`, the agent's note → `comment`; `comment` is documented-required, never server-enforced

- **Decision (the mapping):** Agent capture uses fields that already exist, with **no new text columns and no sentiment enum**. The user's feedback/sentiment goes in **`message`**, free text and verbatim where possible (`답답함`, `감사`, `긍정`, `부정`, `짜증`, or a whole sentence). The agent's note about that feedback — what happened, what the user was doing, why it was recorded — goes in **`comment`**. `tags` stays optional labelling, and `source.integration` stays a free-text runtime hint that is explicitly **not** the marker.
- **Why:** Free text over an enum was the operator's explicit call, so both halves must be free text and both belong in existing fields. Decisively, `message` and `comment` are **both already inside the `pg_trgm` search expression**, so sentiment and note become searchable — Korean substrings included — with **zero** index work (verified live). A new `sentiment` or `note` column would need a migration, would fragment the search target (which would then need its own migration plus a lock-step change in `repository._feedback_search_target()`), and would buy nothing the existing fields do not already give. `trigger_message` was considered for the note and rejected: it describes the UI/action that *caused* capture, not the recorder's commentary.
- **Decision (enforcement):** `comment` is **documented as required for agent capture** in the public skill and docs, and is **not** made server-side mandatory. The intent stated the note as a **capability** requirement — the capturing agent *must be able to* pass a free-text note — and that is satisfied by `comment` existing on every capture surface (REST, MCP, and `vocky capture --comment`).
- **Why not enforce it:** A server-side requirement would `400` every existing REST/CLI/MCP client that omits `comment`, which breaks the phase's own additivity bar for a documentation problem. If it is ever enforced, the only defensible shape is **"required *when* `recorded_by == "agent"`"** — conditional on the marker, never global. That remains an **open question for the operator**, deliberately not decided here.
- **Decision (the CLI):** The `vocky capture` CLI deliberately gains **no marker flag**, on either the write or the read side. `cli/capture.py:_build_payload` hand-builds a subset body (it sends no `trigger_type` and no `channel` either) and `feedback show` prints a curated subset that omits `trigger_type`, so adding the marker there would be a scope change rather than parity. The public docs say plainly that a CLI capture lands `null` and point at REST or `/mcp` when the marker matters.
- **Consequences:** An agent that sends only a sentiment produces a valid but less useful record, and nothing in the service objects — the quality bar lives in the published skill, not the schema. Anyone reading only `api.md`'s field list would not know `comment` is expected for agent capture; that is why the convention is stated in the Shared Capture Provenance Rules there as well as in the skill.
