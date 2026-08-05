---
doc_id: product
version: v0012
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: agent-recorded feedback is a public product surface and the skill now teaches it
previous: v0011_p12_vocky_is_live_at_vocky.hi2vi.com_the_deploy_kit_p6_authored_has_been_executed
---

# Product

## Status

Vocky is pre-MVP and mid-pivot from a self-hosted single-tenant capture service into a **free multi-tenant SaaS**. The capture/review core is implemented with server-to-server REST capture, a scoped end-user REST read, Admin REST, PostgreSQL persistence, Redis-backed queueing, a background worker, and Compose-first local verification. (The self-hosted operator **Admin Web UI** that once shipped inside the service — dashboard metrics, review management, in-app documentation, REST capture try-it — was superseded by the web app in P4 and **physically removed in P6**; Admin REST itself is unchanged.) As of **P7** the agent-decided capture path is back as a **write-only MCP surface**: an AI agent linked to a project's Vocky MCP endpoint saves feedback at its own judgement through a single `capture_feedback` tool, feeding the same queue/store as REST and scoped by the project's `vk_` credential. It is write-only — the three MCP read/query tools retired in P1 stay retired (reads remain REST-only).

The SaaS accounts and tenancy core is now in place: real user accounts (email + password signup/login), a multi-tenant model (tenants → projects), and per-project ingest credentials. The old optional static `VOCKY_API_AUTH_TOKEN` bearer for `/api/*` has been retired in favor of **mandatory per-project credential auth**. Feedback is now **project-scoped**: every captured event records its project, an external service's own admin panel can read and manage its project's feedback directly over a project-scoped REST API (Feedback API v2, `/api/project/feedback`), signed-in users can read and search feedback across all their projects (`/app/feedback`, Korean-safe), and per-tenant/project usage monitoring surfaces derived capture volume and credential last-used (operational visibility only — no billing or metering). As of **P4** vocky has its own **authenticated web app** — sign up in a browser, see your tenant dashboard, drill into a project, mint/revoke `vk_` keys, and search feedback across your projects (Korean-safe). It is now vocky's **only** browser surface — it superseded the packaged self-hosted operator Admin Web UI in P4, and **P6 deleted that old UI outright**. As of **P5** vocky also has a **`vocky` command-line client**: a user — or a coding agent acting for them inside Claude Code or Codex — can sign up, log in, manage projects, mint `vk_` keys, and read/search feedback **entirely from the terminal without visiting the website**, driven headlessly (`--password-stdin`, `--base-url`, `VOCKY_CONFIG_DIR`). **P8→P9** designed and applied the round-01 brand across the app and built the public landing, and **P6** finished the production edges: site metadata/OG/robots/sitemap, a production CSP, and a complete deploy kit for `vocky.hi2vi.com`.

As of **P10** the accounts plane is **user → org → project**, and two user-visible things changed. **Signup now lands a usable account** — it creates the org *and* a `"default"` project, so nobody starts at zero projects with a manual setup step ahead of them. And **a `vk_` key is now a choice of scope**: the existing narrow project key, or a new **org key** that works across every project in the org (with capture naming its project). Both live side by side in the dashboard and the CLI; every existing project key behaves exactly as before. The convenience is real and so is the cost — an org key is a bigger secret, and revoking it cuts every project at once (see `security.md`).

As of **P11** the onboarding story is real end to end for a coding agent, and the last untrue lines on the landing page are gone. Distribution is settled — **a `curl | bash` installer served from the site, not PyPI** — and the two things that made the story unusable are fixed: **`VOCKY_API_TOKEN` now exists** with `vocky capture` as its first-class consumer, so **two environment variables are the whole agent contract**, and vocky **publishes an end-user agent skill** (`vocky-feedback`) on the landing behind a byte-parity CI gate. See "Distribution and Availability" and "The agent-skill surface" below.

**What is still true today: nobody outside this repo can use vocky.** The product is deploy-*ready* and not deploy-*ed* — `vocky.hi2vi.com` does not answer, and nothing is published to PyPI. Public availability now needs exactly one more phase: **P12** performs the live production bring-up (and the `git push` the installer's target depends on). The contracts should still be treated as early-stage.

## Summary

Vocky is a feedback layer for products and the surfaces around them. It captures human-triggered user feedback from websites and product experiences, structures it into usable signals, and helps teams understand what customers are asking for, praising, or struggling with. It is delivered as a free multi-tenant SaaS: a user signs up and immediately has an **org** with a `"default"` project, then mints a `vk_` key — scoped to one project or to the whole org, their choice — that their product backend uses for server-to-server capture. There are no paid plans or billing — the service is free.

## First MVP

The first MVP is intentionally narrow:

- Real user accounts (email + password signup/login) over a multi-tenant core: each account owns an **org** with projects (one, `"default"`, provisioned at signup) and ingest credentials at **project or org** scope
- Free service — no paid plans, billing, usage metering, or plan tiers
- Server-to-server REST ingestion for explicit human-triggered website or product feedback, gated by a mandatory per-project credential
- A write-only MCP `capture_feedback` tool at `/mcp` for agent-decided capture, gated by the same per-project credential and feeding the same store as REST (no MCP read tools)
- Async capture that accepts quickly over REST and persists in the background
- Explicit user action feedback capture, including like/dislike values, optional comments, conversation context, and basic metadata
- A scoped end-user REST read that returns one user's own records plus operator comments
- Optional exact-target metadata for the message, conversation, or product surface being reviewed
- Dedicated Admin REST endpoints for human/operator review and management of stored feedback
- An **authenticated web app** where a user signs up, sees their tenant dashboard (projects + usage), drills into a project to mint/revoke per-project keys, and reads/searches feedback across their projects — vocky's primary user surface
- A **`vocky` CLI** — a first-class terminal user surface alongside the web app — that drives the same accounts → tenant → projects → `vk_` key → capture → read/search spine from the command line, built agent-first (headless `--password-stdin`, `--base-url`, `VOCKY_CONFIG_DIR`) so a coding agent can onboard a user without the website. Distributed as a console script, today only from a checkout (`uv tool install .` / `uvx --from .`). P6 packaged it as a **lean CLI** (httpx + typer) with the server stack behind a `[server]` extra; **the publish itself is P11's decision, and nothing is on PyPI**
- ~~A self-hosted operator Admin Web UI loading from the Vocky app~~ — **removed in P6.** It was superseded by the web app in P4 and no longer exists; Admin REST (`/admin/api/*`) remains as an API-only operator surface
- Nullable channel category assignment for review workflows, using the built-in MVP categories `web`, `mobile`, and `support`
- PostgreSQL storage with Redis-backed background persistence

The MVP does not need automated classification, managed-cloud capabilities, or a production-grade analytics workspace.

## Target Users

- Teams building web and product experiences
- Developers integrating human-triggered feedback capture into product backends
- Product and operations teams reviewing customer voice from product interactions

## Problem

- Product surfaces and customer interactions contain feedback that usually gets buried in logs.
- Teams need structured feedback, not raw log or support noise.
- Feedback should be reviewable, trendable, and usable for prioritization.

## Goals

- Capture explicit human-/product-triggered feedback through server-to-server REST without making clients wait on persistence
- Store explicit user action feedback with enough summary text, exact target, surrounding context, comment, and metadata detail for later review
- Make stored feedback reviewable through a scoped end-user read and Admin REST review surfaces
- Surface simple counts and trends without building a full analytics product
- Give a signed-in user a browser surface for their own tenant: projects, per-project credentials, usage, and cross-project feedback search (the web app, P4)
- Provide a first browser-based operator entry point for self-hosted review and documentation workflows — *met historically by the packaged Admin Web UI; superseded by the web app in P4 and removed in P6*
- Keep the first release practical for community and self-hosted use
- Keep the self-hosted release path verifiable with local smoke checks and public custom-domain smoke checks when an external URL is configured (the packaged Admin UI asset check went away with the UI in P6)

## Non-Goals for Now

- Automatic classification or taxonomy assignment
- A production-ready analytics suite
- Browser-direct unauthenticated ingestion paths
- Broad *unauthenticated* public REST review/query/management. Review, query, and management of stored feedback are now first-class but always **scoped and authenticated**: a project's `vk_` credential reads and manages **its own project's** feedback over `/api/project/feedback` (Feedback API v2), a signed-in user reads and searches feedback across **all their own projects** over `/app/feedback`, and the end-user self-read (`GET /api/feedback`) still returns a single caller-identified user's own feedback (scoped by `user_id` + `source_product`, and now the credential's project). There is no unscoped or cross-tenant public query surface. (Admin REST remains the self-hosted operator surface over the same records.)
- Custom channel category management, deployment-configured channel lists, or automatic channel classification
- Paid plans, billing, usage metering, or plan tiers — the SaaS is free
- Enterprise-grade compliance or heavyweight org/admin workflows
- Multi-user tenant collaboration UI (invites, roles): the tenancy schema supports members and roles, but the MVP flow is solo-owner and the invite/role management surface is out of scope for now
- Finalized public API commitments

## Product Direction

- Community and self-hosted usage are part of the base direction.
- The first MVP should optimize for self-hosted deployment before managed concerns.
- Self-hosted deployments may be local/private or publicly reachable behind an operator-managed custom domain, provided public REST capture and Admin REST access are protected where exposed.
- The **web app is vocky's browser surface** for signed-in users (P4): account signup/login, tenant dashboard, project detail with credential mint/revoke, and cross-project feedback read/search. It is a session-authed client of `/auth/*` + `/app/*` and adds no capability the API does not already have. Feedback **management** deliberately stays out of it (a product's own admin panel does that with its `vk_` key over `/api/project/feedback`); the web app is where a human *finds* feedback across projects.
- The Admin Web UI was the first browser-based operator entry point for self-hosted deployments. **P4 superseded it by replacement rather than repair** — the web app is the browser surface going forward — and **P6 completed the retirement by deleting it** (module, packaged assets, `/admin` + `/admin/assets/*` routes, and the wheel asset check). Its packaged in-app docs, which still described the retired static-token model, went with it. Admin REST (`/admin/api/*`) and its separate bearer boundary are unaffected; it simply has no first-party client any more.

## Distribution and Availability (P6, decided in P11)

Two facts about how a real user would get vocky, both currently **not yet true in the world**:

- **vocky is live at `https://vocky.hi2vi.com`** (since 2026-08-04, P12). The production deploy kit P6 authored — container images, compose topology, edge nginx vhost, deploy/rollback scripts, and the GitHub Actions chain — has now been executed against real infrastructure, green on its first run. Sequencing the bring-up after P10 paid off exactly as intended: the accounts-v2 schema changes landed on an **empty** database rather than as a live cutover on production data. The hosted `curl … | bash` install line works today; a signup → session round-trip was proven live at the bring-up.
- **The install channel is decided, and it is not PyPI.** **P11 chose a `curl | bash` installer** — `web/public/install.sh`, served at `https://vocky.hi2vi.com/install.sh` — at zero infra cost: the site already serves `web/public/*`, so there is no route, MIME or packaging work, and no irreversible publish. Nothing was uploaded to PyPI and `uv publish` remains an unexercised, operator-gated action; P6's lean-CLI/`server`-extra split still describes the dependency surface either way (`pip install vocky` would be httpx + typer only; `pip install "vocky[server]"` the full self-hosted stack). Today the only install path is from a checkout of this repo, and the hosted line becomes true the moment P12 deploys — the landing page and the installer ship together, so no live page ever serves a dead command.

Until both land, vocky's audience is this repo. Nothing in the product should be described to users as available.

## The agent-skill surface (P11)

Vocky's onboarding has an explicit audience beyond a product backend: **a coding agent acting for a user**. As of P11 that path is a product surface rather than an implication.

- **Two environment variables are the whole contract** — `VOCKY_BASE_URL` and `VOCKY_API_TOKEN`. Nothing else: no plugin to install, no SDK, no config file, no per-repo setup. Two exports (recommended in `~/.zshenv`, never a repo `.env`) give every coding agent on the machine the same access.
- **`VOCKY_API_TOKEN` carries the `vk_` key and only the `vk_` key.** It is never the session token, is never persisted to the config store, and has no `--token` flag counterpart — argv is world-readable. The two credentials are structurally prevented from crossing.
- **There are three capture paths, and the product names them in that order**: the **CLI** (`vocky capture`, one command — the primary path), **raw REST** (`POST /api/feedback`, no vocky install required), and **`/mcp`** (the same `vk_` bearer, the single `capture_feedback` tool). All three hit the same contract; none of them is new backend capability — **P11 added no capture contract**, and `POST /api/feedback` is byte-for-byte the P10 shape.
- **The skill itself is a published artifact**: `skills/vocky-feedback/SKILL.md`, served byte-identically at `/SKILL.md`, presented on the landing page for reading, copying and download, and held to the canonical by a CI byte-parity gate so the published copy can never fork. It is written to be executed verbatim — exact commands, a zero-side-effect verify step, and a branch-by-branch error table with an explicit "stop, do not retry" on `401`. **As of P14 it also carries the agent-capture contract** — the sentiment/note field mapping, the `recorded_by` marker with its per-transport default, and a plain-spoken statement of what a `vk_` key can actually do — which grew its numbered walk from **7 steps to 8** (the new field-mapping step precedes the three capture paths). Still one canonical file plus a byte-identical served copy behind the same gate.

## Agent-recorded feedback (P14)

Vocky publicly supports **agent-recorded feedback**: a third-party AI agent decides mid-conversation that something a user said is worth keeping — 답답함, 감사, 긍정, 부정, 짜증, or a whole sentence — and records it, together with its own free-text note, so product operators hear the raw voice of the customer. The first real consumer is an external chat product, but the surface is **public**: anyone's agent can adopt it exactly the way that product does, from the published docs alone.

- **Free text, no enum — the product decision.** There is no fixed sentiment vocabulary to map onto and no normalization. The user's own words go in the feedback `message` verbatim; the agent's note about what happened goes in `comment`. Both are already searchable, Korean included.
- **The agent-vs-human distinction is first-class, not a convention.** Vocky persists `recorded_by` (`agent` / `human`), so agent-recorded feedback is queryable and filterable everywhere feedback is read, and a dashboard can genuinely separate the two. Before P14 the only hint was a free-text integration label, which nothing validated and nothing could filter on.
- **Unspecified is a real third state.** Everything captured before this feature — and anything captured without stating the marker — reads back as *unspecified*, never as "human". Vocky does not backfill and does not guess.
- **The agent runtime is the one place it is inferred.** Capture over `/mcp` is agent capture by construction, so the marker defaults to `agent` there and an agent that never learns the argument still produces correct data. REST and the CLI never guess.
- **Adoption costs existing users nothing.** Every existing product backend, CLI user, dashboard, and agent keeps working byte-for-byte; the contract only grew.
- **Not built, deliberately:** a visible agent-vs-human filter control or split view in the dashboard. That is product visual design and belongs to a design phase, not a contract phase; today the split is available by URL and by API.

**Honesty was the gate on all of it.** The landing page previously published two things that were simply not true — a top-level `source_product` (the capture request nests it) and a `vk_live_` key tier that has never existed — and both were corrected before anything new was designed on top of them. Nothing on the landing may claim a command works before the artifact behind it ships.
- `/api/*` ingest auth is now mandatory per-project credential auth: a product backend mints a `vk_` key for its project through the control-plane and sends it as `Authorization: Bearer` on every capture/read request. The old optional static global `VOCKY_API_AUTH_TOKEN` bearer is retired.
- The default local workflow should stay loopback-first and Compose-first, while public custom-domain access should be operator-managed through an HTTPS reverse proxy such as Cloudflare Tunnel and verified separately from local checks.
- The capture path should acknowledge accepted work quickly and complete persistence asynchronously in the background.
- The REST capture path is the sole ingestion path for explicit human-triggered product/UI feedback, such as like/dislike controls, page feedback, widgets, surveys, or other product-surface feedback, using the shared capture fields instead of REST-only aliases or a separate endpoint.
- The REST capture path remains capture-only, with one deliberate exception: a narrowly scoped end-user self-read (`GET /api/feedback`) that returns a single user's own feedback plus operator comments, scoped by required `user_id` and `source_product`. In-app try tooling may exercise capture, but broad review, query, summary, job-status, and management remain Admin REST concerns rather than new public REST endpoints.
- Operator comments are a first-class concept distinct from the end user's own `comment`: operators add and list them through Admin REST, and the scoped end-user read surfaces them read-only to the originating user as one-way operator-to-user visibility.
- End users can attach images (such as screenshots) to feedback. Images are uploaded synchronously to obtain an attachment id that the capture call references, and the worker links them to the feedback record after persist. Attachments appear in both the operator-review and scoped end-user-read responses and are served through authenticated downloads: an end user can download only their own attachments (scoped by `user_id` + `source_product`), while operators can download all attachments for the feedback they review. Allowed types and size are operator-configurable; the default is common raster image types up to a few megabytes.
- The initial high-signal capture path should focus on explicit user actions, such as like/dislike clicks and optional comments, rather than trying to infer feedback from every interaction.
- Optional caller-owned user identity and trigger context fields preserve who the product associates with the event and which action, control, survey, or manual workflow caused capture.
- Feedback capture should not assume that the latest message is the reviewed item. Callers should identify the exact reviewed message, conversation, or product surface when that information is available.
- Message, conversation, and non-message surface feedback should stay in the same canonical feedback store and be separated for review through `target_type`, not through split tables or separate capture endpoints.
- `target_type` is an exact-match review filter for separating `message`, `conversation`, and `surface` feedback.
- `channel` should be a nullable review category, not open-ended free text. New captures and Admin edits should leave it unset by default unless the caller or operator explicitly selects one of the built-in MVP categories: `web`, `mobile`, or `support`.
- Existing stored records with older arbitrary channel text should remain reviewable and filterable, but new writes should not create new arbitrary channel values.
- A managed offering may exist later around convenience, operations, and richer workflows.
- The repo should stay honest about what is planned versus what is already implemented.

## Accounts: user → org → project (P10)

Vocky is a multi-tenant SaaS, and as of **P10** the model is explicitly **user → org → project**:

- A **user** authenticates with an email and password. **Signup lands a ready-to-use account**: it provisions the user, their **org** (auto-named `"<email-local-part>'s workspace"`), their sole `owner` membership, **and a project named `"default"`** — all in one step. Before P10 a new account arrived with zero projects and zero keys, so the "create a project, mint a key" step was manual dashboard work; now it is done for you. Login and signup mint an opaque session bearer token. The schema supports multiple members with roles, but the MVP flow is solo-owner.
- **Only the *project* is named `"default"`; the org keeps its friendly name.** Vocky deliberately does not name the org `"default"` — nothing resolves an org by name, the friendly name is what the app shell shows the user, and a literal would make the product worse to look at for no gain. Note this contradicts an earlier phrasing of the P10 objective, which said signup provisions a "`default` org and a `default` project": only the project half is true, and the docs follow the code.
- An **org** owns **projects**, and **project names are unique per org**. Creating a project by a name that already exists returns the existing one rather than erroring or duplicating, which makes "make sure this project exists" a safe, repeatable operation for scripts and agents.
- **A key is a choice of scope, and the user makes it.** There are two kinds, both `vk_`-prefixed, both shown exactly once at creation and stored only as a hash:
  - a **project key** — the narrow default, works for one project;
  - an **org key** (P10) — one key that works across **every** project in the org, including projects created later. When capturing with an org key the caller names the project (get-or-created, defaulting to `"default"`), so one key can feed many projects.
  The trade-off is stated rather than hidden: an org key is more convenient and a bigger secret — revoking it cuts every project at once. The two are managed side by side in the dashboard and from the CLI. Existing project keys are completely unaffected by the addition.
- A user manages all of this through the account control-plane (`/app/*`, session-token authed) — directly over the API, point-and-click in the **web app** (P4), or from the **CLI** (P5).
- The service is free — accounts, orgs, projects, and credentials carry no billing, metering, or plan tiers.
- **Not in scope yet:** creating additional orgs, inviting members, and roles. Every account has exactly one org today; the schema anticipates more, the product does not offer it.

**Naming note.** The database table is still `tenants` and every API field is still `tenant_id` — "org" is the product-facing word, adopted in the app, the CLI, and these docs. The two mean the same thing.

## Product Surface Roles

Vocky uses one canonical feedback store and one shared capture field set, but the public-facing surfaces have different jobs:

- The **account auth** surface (`/auth/*`) is public and unauthenticated-to-enter: `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, and `GET /auth/me` establish and inspect a user session.
- The **account control-plane** (`/app/*`, session-token authed) is where a user reads their org, creates/lists/reads projects, and mints/lists/revokes credentials at **either** scope — per-project under `/app/projects/{id}/credentials`, org-level under `/app/credentials` (P10). The two surfaces are disjoint: an org key is invisible and unrevokable through the per-project routes, and a project key likewise through the org routes. It is tenant-scoped: a caller can never see or touch another tenant's projects or credentials. It also hosts the signed-in user's **cross-project feedback read + search** (`/app/feedback`: list/search across all their projects, get-one, attachment download — Korean-safe substring search, read-only) and **usage monitoring** (`/app/usage` whole-tenant capture volume + a project list; `/app/projects/{id}/usage` one project's volume + its credentials' last-used). Every read answers 404 (never 403) on a cross-tenant id.
- **Public REST** (`/api/*`) is for trusted server-to-server product integrations and requires a valid per-project credential on every request. It carries: capture (`POST /api/feedback`, `POST /api/feedback/attachments`); the scoped end-user self-read (`GET /api/feedback` + its attachment download, scoped by `user_id` + `source_product` + the credential's project); the project-scoped **Feedback API v2** for an external service's own admin panel (`/api/project/feedback`: list/get/PATCH review fields/DELETE/operator comments/attachment download over **its own project's** feedback, 404 on any cross-project id); and scoped usage (`GET /api/project/usage`: the credential's capture volume + its credentials). A `vk_` key thus does capture **and** read+manage across **its scope** — one project for a project key, the whole org for an org key. There are still no per-credential permission scopes: P10 widened *what a key can reach*, not *what it may do* there.
- **MCP capture** (`/mcp`) is the agent-decided **write-only** ingress (P7): an AI agent linked to a project's Vocky MCP endpoint calls the single `capture_feedback` tool to save feedback at its own judgement. The whole endpoint is authed by the project's `vk_` credential (the same boundary as `/api/*`), and captured events feed the same shared queue/store scoped to that credential's project. There are no MCP read/query tools — reads stay on the REST/`/app` surfaces above. **As of P14 this is a publicly documented third-party surface** (see "Agent-recorded feedback" above): it takes the `recorded_by` marker and is the one transport that defaults it to `agent`.
- **The web app** (P4) is the **browser** surface over the account control-plane above — vocky's primary user-facing surface. A user signs up, lands on a tenant dashboard (projects + usage totals + daily trend), drills into a project (its usage, its credentials' last-used, mint a show-once `vk_` key, revoke one), and reads/searches feedback across all their projects. It is session-authed through a server-side proxy: the browser never holds the vocky token and never calls `/api/*`. It carries **no feedback management** by design, and answers 404 (never 403) on anything outside the signed-in user's tenant.
- **The `vocky` CLI** (P5) is the **terminal** surface over the same account control-plane — vocky's agent-first onboarding path. `vocky signup|login|logout|whoami` (over `/auth/*`), `vocky projects`, `vocky keys` (show-once `vk_` mint), and `vocky usage` (over `/app/*`), and read-only `vocky feedback list|search|show` (over `/app/feedback`). It carries no feedback management, and answers 404 (never 403) outside the caller's tenant. It adds no backend capability; it makes the whole spine completable headlessly from a coding agent (`--password-stdin`, `--base-url`, `VOCKY_CONFIG_DIR`). **As of P11 the CLI straddles both auth planes, deliberately and in exactly one place**: every command above is a session-token client of `/auth/*` + `/app/*`, while the new `vocky capture` (P11) is the sole `vk_`-keyed command, reading its key from `VOCKY_API_TOKEN` and posting to `/api/feedback`. The two credentials cannot cross — `capture` never sends the stored session token and the `vk_` key is never persisted. Full reference in `docs/cli.md`.
- **Admin REST** is for human/operator review and management. `/admin/api/*` powers dashboards, list/detail inspection, review-field editing, metrics, and deletion over the same stored feedback records. It keeps its own separate `VOCKY_ADMIN_AUTH_TOKEN` bearer (untouched by the accounts/feedback-API work).

## Current Field Taxonomy

Current feedback fields are grouped by responsibility, not by transport. Public REST capture uses this field set; Admin REST reviews and manages the stored record shape.

- Display and action fields: `message`, `feedback_value`, and `comment` describe the visible feedback record and explicit like/dislike/comment action.
- Source identity fields: `source.product` and `source.integration` identify the product and integration that sent the feedback. Stored records expose them as `source_product` and `source_integration`.
- Caller identity fields: `user_id` optionally identifies the caller-owned end user, account member, or product user associated with the feedback. It is distinct from `session_id`, which remains runtime, browser, or session correlation.
- Capture provenance field: `recorded_by` records **who recorded the event** — an AI agent or a person — and is deliberately orthogonal to the trigger fields' *why capture happened*. It is set once at capture, is never editable, and is unset (*unspecified*) rather than assumed when the caller does not state it.
- Trigger fields: `trigger_type`, `trigger_message`, and `trigger_metadata` describe the user action, UI control, survey, manual workflow, or other product event that caused capture. They do not replace the primary feedback `message`, optional user `comment`, target fields, process context, or source metadata.
- Review category fields: `channel` and `tags` support operator filtering and review organization without changing the target of the feedback.
- Exact target fields: `target_type`, `target_id`, `target_role`, and `target_text` identify the reviewed message, conversation, or product surface when the caller knows it.
- Conversation and session context fields: `conversation_id`, `session_id`, and `messages` group feedback with surrounding runtime or conversation context.
- Agent and process context fields: `used_context` preserves context the agent used while generating the reviewed response.
- Metadata fields: `event_at`, `ingested_at`, `source_metadata`, `attributes`, and generated record identifiers preserve timing, source-specific details, product-specific dimensions, and storage identity.

## Terminology

- `VoC`: voice of customer
- `user` / `account`: a Vocky user identified by email, authenticated with a password. Distinct from the capture `user_id`, which identifies an integrating product's own end user.
- `org`: the product-facing name for a tenant — the container a user's projects live in. Signup auto-creates one per user, named `"<email-local-part>'s workspace"`, with that user as sole `owner`. Additional orgs, invites, and roles are not offered yet.
- `tenant`: the **implementation** name for an org. The table is `tenants`, the field is `tenant_id`, and neither was renamed in P10 — a rename would be a large mechanical change with zero behavior difference. Read `tenant` and `org` as the same thing; prefer "org" in anything user-facing.
- `project`: a named unit under an org that groups feedback ingestion and owns project-scoped credentials. **Names are unique per org**, and creating one by an existing name returns the existing project. Every account starts with one, named `"default"`.
- `project key` (project-bound credential): a `vk_`-prefixed opaque ingest key scoped to **one project**. The plaintext is shown once at creation and only a hash is stored; it authenticates `/api/*` capture, read, and manage for that project and can be revoked.
- `org key` (org-level credential, P10): a `vk_`-prefixed key scoped to **the whole org** — every project in it, including ones created later. Same prefix, same show-once handling, same verbs; broader reach. When capturing, the caller names the destination project (get-or-created, defaulting to `"default"`). Revoking it cuts every project at once.
- `session token`: the opaque bearer token minted on signup/login for the account control-plane (`/auth/*`, `/app/*`). Stored only as a hash, with a 30-day expiry.
- `message`: the required human-readable feedback summary or display text. It is the text Vocky shows as the primary feedback record label, not an implicit pointer to the reviewed agent message.
- `comment`: the end user's own optional comment captured at feedback time. It is distinct from an operator comment.
- `operator comment`: an operator-authored note attached to a stored feedback event, kept in a separate store keyed by feedback id. Operators add and list operator comments through Admin REST; the scoped end-user read returns them read-only to the originating user. `author` is an optional caller-supplied operator label because Vocky has no native operator accounts.
- `conversation_id`: caller-provided conversation or thread identifier used to group feedback from the same conversation.
- `session_id`: optional caller-provided runtime, browser, or user-session identifier. It can help correlate repeated interactions without replacing `conversation_id`.
- `user_id`: optional caller-owned user or account-member identifier associated with the feedback event. Vocky treats it as an opaque string and does not infer authentication, tenancy, or identity semantics from it.
- `trigger_type`: optional category for the action or workflow that caused capture. Accepted P1 values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`.
- `trigger_message`: optional human-readable action label, prompt copy, button text, survey question, or event description that caused capture. It explains why capture happened; it is not the primary feedback `message` or the user's `comment`.
- `trigger_metadata`: optional structured object for trigger-specific context, such as rating scale, selected option, control id, experiment id, or redacted UI/runtime details.
- `channel`: optional nullable review category for where the feedback came from. The MVP built-in categories are `web`, `mobile`, and `support`; `null` means no channel category was assigned.
- `feedback target`: the exact reviewed item, when known. It may be a message, a whole conversation, or a non-message product surface.
- `target_type`: optional feedback target category. The MVP target categories are `message`, `conversation`, and `surface`; `null` means the caller did not identify an exact target category.
- `target_id`: optional stable caller-provided identifier for the target, such as a message id or UI surface id.
- `target_role`: optional role for message targets. The MVP roles are `user`, `assistant`, `system`, and `tool`.
- `target_text`: optional snapshot of the exact reviewed message or product surface text at capture time.
- `messages`: optional surrounding conversation context supplied by the caller. It is context for review, not the authoritative target by itself.
- `used_context`: optional context the agent used while generating the reviewed response, such as retrieved documents, snippets, or tool context.
- `surface feedback`: REST-captured explicit product/UI feedback about a page, widget, screen, or other non-message product surface. It should use `target_type="surface"` when the exact surface is known, plus optional `target_id`, `target_text`, `source_metadata`, and `attributes` for product-specific context.
- `phase`: a grouped unit of work in `works/backlog.md`
- `slice`: a concrete step inside a phase
- `work item`: a timestamped execution folder under `works/current/` or `works/archives/work_items/`
