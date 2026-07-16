---
doc_id: product
version: v0004
created_at: 2026-07-16T16:32:58+09:00
source: P3.REVIEW
summary: P3: feedback is project-scoped; add project-scoped Feedback API v2 (read+manage), cross-project search, and operational usage monitoring (no billing); flip the broad-public-REST-management non-goal
previous: v0003_free_multi-tenant_saas_core_accounts_tenants_projects_per-project_credentials_no_billing
---

# Product

## Status

Vocky is pre-MVP and mid-pivot from a self-hosted single-tenant capture service into a **free multi-tenant SaaS**. The capture/review core is implemented with server-to-server REST capture, a scoped end-user REST read, Admin REST, a self-hosted operator Admin Web UI with dashboard metrics, feedback review management, in-app documentation, and REST capture try-it, PostgreSQL persistence, Redis-backed queueing, a background worker, and Compose-first local verification. The earlier AI-agent-decided MCP capture and MCP read tools have been retired (recoverable through git history).

The SaaS accounts and tenancy core is now in place: real user accounts (email + password signup/login), a multi-tenant model (tenants → projects), and per-project ingest credentials. The old optional static `VOCKY_API_AUTH_TOKEN` bearer for `/api/*` has been retired in favor of **mandatory per-project credential auth**. Feedback is now **project-scoped**: every captured event records its project, an external service's own admin panel can read and manage its project's feedback directly over a project-scoped REST API (Feedback API v2, `/api/project/feedback`), signed-in users can read and search feedback across all their projects (`/app/feedback`, Korean-safe), and per-tenant/project usage monitoring surfaces derived capture volume and credential last-used (operational visibility only — no billing or metering). Still upcoming in later phases: the tenant/project web app (P4); a CLI + agent-first onboarding path (P5); and the landing page plus production deploy (P6). The contracts should still be treated as early-stage.

## Summary

Vocky is a feedback layer for products and the surfaces around them. It captures human-triggered user feedback from websites and product experiences, structures it into usable signals, and helps teams understand what customers are asking for, praising, or struggling with. It is delivered as a free multi-tenant SaaS: a user signs up, gets a tenant (workspace) with projects, and mints per-project credentials that their product backend uses for server-to-server capture. There are no paid plans or billing — the service is free.

## First MVP

The first MVP is intentionally narrow:

- Real user accounts (email + password signup/login) over a multi-tenant core: each account owns a tenant (workspace) with projects and per-project ingest credentials
- Free service — no paid plans, billing, usage metering, or plan tiers
- Server-to-server REST ingestion for explicit human-triggered website or product feedback, gated by a mandatory per-project credential
- Async capture that accepts quickly over REST and persists in the background
- Explicit user action feedback capture, including like/dislike values, optional comments, conversation context, and basic metadata
- A scoped end-user REST read that returns one user's own records plus operator comments
- Optional exact-target metadata for the message, conversation, or product surface being reviewed
- Dedicated Admin REST endpoints for human/operator review and management of stored feedback
- A self-hosted operator Admin Web UI that loads from the Vocky app, uses Admin REST as its protected data boundary, and includes dashboard metrics, feedback list/filter/detail/edit/delete workflows, in-app operator documentation, and an operator-only REST capture try-it flow
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
- Provide a first browser-based operator entry point for self-hosted review and documentation workflows
- Keep the first release practical for community and self-hosted use
- Keep the self-hosted release path verifiable with local smoke checks, packaged Admin UI asset checks, and public custom-domain smoke checks when an external URL is configured

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
- The Admin Web UI is an operator surface for self-hosted deployments. It should stay same-origin with the app, use Admin REST for protected data, include practical dashboard metrics, feedback review management, operator documentation, and an operator-only REST capture try-it flow, and avoid managed-SaaS assumptions.
- `/api/*` ingest auth is now mandatory per-project credential auth: a product backend mints a `vk_` key for its project through the control-plane and sends it as `Authorization: Bearer` on every capture/read request. The old optional static global `VOCKY_API_AUTH_TOKEN` bearer is retired. (The packaged Admin Docs try-it flow still references the old token and is deferred to P4's operator-surface reshaping; its guidance no longer reflects the live auth model.)
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

## Accounts and Tenancy

Vocky is a multi-tenant SaaS. The identity and tenancy model is:

- A **user** authenticates with an email and password. Signup provisions the user, creates their **tenant** (workspace, auto-named from the email local part), and adds them as its sole `owner` member; login and signup mint an opaque session bearer token. The tenancy schema supports multiple members with roles, but the MVP flow is solo-owner.
- A **tenant** owns **projects**. A user manages their tenant and projects through the account control-plane (`/app/*`, session-token authed).
- Each project mints **per-project credentials** (`vk_`-prefixed keys). A credential's plaintext key is shown exactly once at creation; only a hash is stored, so it is never recoverable. Keys can be listed (metadata only) and revoked. A product backend sends a project key as `Authorization: Bearer` on `/api/*` to capture feedback for that project.
- The service is free — accounts, tenants, projects, and credentials carry no billing, metering, or plan tiers.

## Product Surface Roles

Vocky uses one canonical feedback store and one shared capture field set, but the public-facing surfaces have different jobs:

- The **account auth** surface (`/auth/*`) is public and unauthenticated-to-enter: `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, and `GET /auth/me` establish and inspect a user session.
- The **account control-plane** (`/app/*`, session-token authed) is where a user reads their tenant and creates/lists/reads projects and mints/lists/revokes per-project credentials. It is tenant-scoped: a caller can never see or touch another tenant's projects or credentials. It also hosts the signed-in user's **cross-project feedback read + search** (`/app/feedback`: list/search across all their projects, get-one, attachment download — Korean-safe substring search, read-only) and **usage monitoring** (`/app/usage` whole-tenant capture volume + a project list; `/app/projects/{id}/usage` one project's volume + its credentials' last-used). Every read answers 404 (never 403) on a cross-tenant id.
- **Public REST** (`/api/*`) is for trusted server-to-server product integrations and requires a valid per-project credential on every request. It carries: capture (`POST /api/feedback`, `POST /api/feedback/attachments`); the scoped end-user self-read (`GET /api/feedback` + its attachment download, scoped by `user_id` + `source_product` + the credential's project); the project-scoped **Feedback API v2** for an external service's own admin panel (`/api/project/feedback`: list/get/PATCH review fields/DELETE/operator comments/attachment download over **its own project's** feedback, 404 on any cross-project id); and per-project usage (`GET /api/project/usage`: the credential's project capture volume + its credentials). A `vk_` key thus does capture **and** project read+manage for its one project — there are no per-credential scopes in the MVP.
- **Admin REST** is for human/operator review and management. `/admin/api/*` powers dashboards, list/detail inspection, review-field editing, metrics, and deletion over the same stored feedback records. It keeps its own separate `VOCKY_ADMIN_AUTH_TOKEN` bearer (untouched by the accounts/feedback-API work).

## Current Field Taxonomy

Current feedback fields are grouped by responsibility, not by transport. Public REST capture uses this field set; Admin REST reviews and manages the stored record shape.

- Display and action fields: `message`, `feedback_value`, and `comment` describe the visible feedback record and explicit like/dislike/comment action.
- Source identity fields: `source.product` and `source.integration` identify the product and integration that sent the feedback. Stored records expose them as `source_product` and `source_integration`.
- Caller identity fields: `user_id` optionally identifies the caller-owned end user, account member, or product user associated with the feedback. It is distinct from `session_id`, which remains runtime, browser, or session correlation.
- Trigger fields: `trigger_type`, `trigger_message`, and `trigger_metadata` describe the user action, UI control, survey, manual workflow, or other product event that caused capture. They do not replace the primary feedback `message`, optional user `comment`, target fields, process context, or source metadata.
- Review category fields: `channel` and `tags` support operator filtering and review organization without changing the target of the feedback.
- Exact target fields: `target_type`, `target_id`, `target_role`, and `target_text` identify the reviewed message, conversation, or product surface when the caller knows it.
- Conversation and session context fields: `conversation_id`, `session_id`, and `messages` group feedback with surrounding runtime or conversation context.
- Agent and process context fields: `used_context` preserves context the agent used while generating the reviewed response.
- Metadata fields: `event_at`, `ingested_at`, `source_metadata`, `attributes`, and generated record identifiers preserve timing, source-specific details, product-specific dimensions, and storage identity.

## Terminology

- `VoC`: voice of customer
- `user` / `account`: a Vocky user identified by email, authenticated with a password. Distinct from the capture `user_id`, which identifies an integrating product's own end user.
- `tenant`: a workspace owned by users through `tenant_members` rows. Signup auto-creates one tenant per user with that user as the sole `owner`. A tenant owns projects.
- `project`: a named unit under a tenant that groups feedback ingestion and owns per-project credentials.
- `project credential`: a `vk_`-prefixed opaque ingest key scoped to one project. The plaintext is shown once at creation and only a hash is stored; it authenticates `/api/*` capture for that project and can be revoked.
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
