# Phase P3: Feedback API v2, Search & Usage Monitoring

_Intent: see [intent.md](intent.md)._

## Objective

Expose a full tenant/project-scoped REST API over feedback (capture plus get/list/manage) so external services' admin panels can consume feedback directly; add proper feedback search across a user's projects and per-tenant/project usage monitoring.

## Context

Builds on P2's tenants/projects/credentials model. P3 turns feedback from a write-only capture surface into a full project-scoped REST API (get/list/manage) that external services' admin panels can consume directly, plus cross-project search and per-tenant/project usage monitoring. The agent-capture path was already dropped in P1; the API is human-triggered feedback only.

## Decomposition

Four middle slices. **P3.S1 is the foundation; P3.S2, P3.S3, and P3.S4 all depend on it** (they consume the threaded project scope and the `project_id` column). S2/S3/S4 are otherwise independent of each other and could run in any order after S1.

- **P3.S1 — Project-scope foundation** (`medium`, order 1): nullable `project_id` FK on `feedback_events` (+ index), chained on head `20260715_1200`; model field; middleware threads the resolved `credential.project_id` (+ credential id) onto the ASGI scope; capture stamps `project_id` end-to-end (handler → `CreateFeedbackEvent` → `capture_queue` serialize/deserialize → worker → repository); wire the never-called `last_used_at` stamps; tighten the end-user self-read to also scope by project. Update `tests/test_persistence.py` head-pin + index list. _Rationale: everything else needs the column + the threaded scope, so it lands first._ **Everything depends on this.**
- **P3.S2 — `/api/*` project-scoped review + manage** (`medium`, order 2, depends P3.S1): `project_id` scoping in `_apply_query_filters`; project-credential-authed routes (project from scope) that port the `admin_api.py` verbs — list (filters + keyset paging) / get-one (+comments+attachments) / PATCH review fields / operator comments add+list / delete. Distinct pathing from the end-user self-read. _Rationale: the external-admin-panel path — a `vk_` credential reads+manages its own project's feedback._
- **P3.S3 — `/app/*` cross-project read + multilingual search** (`high`, order 3, depends P3.S1): net-new Postgres search migration (extension + trigram GIN per the Korean constraint in D-P3-4); multilingual free-text `q` predicate; session-authed `/app/*` endpoints listing/searching across ALL the caller's tenant's projects (+ optional `project_id` narrowing) + get-one. Consumed by P4 dashboard and P5 CLI. _Rationale: the riskiest slice — net-new search subsystem + the multilingual constraint; hence `high` tier._
- **P3.S4 — Usage monitoring** (`medium`, order 4, depends P3.S1): scope `get_feedback_metrics` / `summarize_feedback` per project/tenant; `/app/*` usage endpoints (capture volume over time by value/channel; surface credential last-used); optionally per-project usage on `/api/*`. _Rationale: derived metrics + last-used surfacing, no new tables._

**Splitting is allowed:** the executor of S2 or S3 **may split** its slice if it proves too large — e.g. S3 → (migration + search predicate) vs (`/app` endpoints) — creating a follow-on slice and recording the rationale here.

## Findings & Notes

- **D-P3-1** Feedback gains nullable `project_id` FK → `projects.id`; capture stamps it from the authenticating credential's project; middleware threads project scope onto the ASGI scope. Legacy rows stay NULL (pre-MVP, no backfill).
- **D-P3-2** "Both, full" scope: a project credential authorizes capture **and** project-scoped read+manage of its own project's feedback on `/api/*` (external-admin-panel path). **No per-credential scopes** in the MVP — one `vk_` key does everything for its project; scopes deferred.
- **D-P3-3** Cross-project read + search live on `/app/*` (session/`require_user`), scoped to the caller's tenant's projects; consumed by P4 dashboard and P5 CLI.
- **D-P3-4 (Korean/multilingual search constraint — operator-stated).** Feedback **may be Korean**. Do **NOT** use `to_tsvector('english', …)` — English stemming is wrong for Korean and Korean particles/조사 defeat word-token matching. Recommended mechanism: **`pg_trgm` trigram GIN** (language-agnostic substring/similarity; handles Korean 조사-attached forms + English uniformly), optionally a `simple`-config `tsvector` for ranking. **The S3 executor must confirm `pg_trgm` (or `pg_bigm`) availability on the target Postgres and record the final chosen mechanism here.**
- **D-P3-5** Usage = derived + last-used, **no new tables**: reuse `get_feedback_metrics` / `summarize_feedback` scoped per project/tenant, and wire the already-built, never-called `touch_credential_last_used` / `touch_auth_token_last_used`. No request-count metering (honors D-P2-7 free/no-billing).
- **D-P3-6** The existing `GET /api/feedback` end-user self-read additionally scopes to the credential's project (defense in depth), once `project_id` is threaded.

### Implementation anchors (so downstream slice plans start grounded)

- Scope-threading hook: `src/vocky/auth.py:98-122`.
- Query chokepoint: `feedback/repository.py:525-567` (`_apply_query_filters`); `tags.contains([...])` at line 565 is the non-equality template.
- Verbs to port: `src/vocky/admin_api.py` (+ `feedback/service.py` already supports them).
- Metrics precedent: `feedback/repository.py:467-523`.
- Last-used stamps: in `accounts/repository.py` (call from the middleware + `accounts/auth.py:require_user`).
- Capture threading: `feedback/types.py` `CreateFeedbackEvent` + `capture_queue.py:56-175` + `worker.py`.
- Migration: head `20260715_1200`; GIN precedent `postgresql_using="gin"`.
- Tests: use real Postgres + the `configured_project_credential` fixture; any new table must be appended to both TRUNCATE lists (`tests/conftest.py:142-155`).

### P3.S1 outcomes — foundation landed (S2/S3/S4 build on these)

- **Migration revision id: `20260716_1500`** (`add_feedback_project_id`, down_revision `20260715_1200`, now head). Any new P3 migration (e.g. S3's search index) must chain `down_revision = "20260716_1500"`. Fully reversible (verified downgrade→upgrade). Adds nullable `feedback_events.project_id` FK → `projects.id` (`ondelete=CASCADE`, name `fk_feedback_events_project_id_projects`) + index `ix_feedback_events_project_id`.
- **Scope-threading contract (S2 reuses):** on a successful `/api/*` auth, `ProjectCredentialAuthMiddleware` stashes the resolved `ProjectCredentialRecord` on the ASGI scope under the namespaced key `vocky.project_credential` (constant `vocky.auth.PROJECT_CREDENTIAL_SCOPE_KEY`). Handlers read it via **`vocky.auth.get_request_credential(request) -> ProjectCredentialRecord`** (carries `.id` + `.project_id`). S2's `/api/*` review/manage routes should scope by `get_request_credential(request).project_id`; **no path params or query for project** — the project comes from the credential. A namespaced scope key (not `request.state`) is deliberate: immune to Starlette `scope["state"]` re-init inside the middleware stack.
- **Read-model hook (S2/S3 reuse):** `FeedbackQueryFilters` gained `project_id: UUID | None = None`; `_apply_query_filters` (`feedback/repository.py`) applies `FeedbackEventModel.project_id == filters.project_id` when set. This is the shared chokepoint — S2 (`/api/*` list) sets it from the credential's project; S3 (`/app/*` cross-project) leaves it unset and instead scopes by the caller-tenant's project set (its own predicate) or sets it for optional single-project narrowing.
- **Capture threading:** `CreateFeedbackEvent.project_id` + `FeedbackEventRecord.project_id` added; threaded handler→`capture_queue` (serialize/deserialize, keeps `project_id` across the Redis round trip)→repository. **Worker unchanged** (it just persists the payload). Attachments were intentionally left without `project_id` in S1 (they inherit scope via their linked feedback row).
- **Last-used stamping wired (D-P3-5 groundwork):** `ProjectCredentialAuthMiddleware` best-effort stamps credential `last_used_at`; `accounts/auth.py::require_user` best-effort stamps auth-token `last_used_at`. Both wrapped in `try/except AccountsPersistenceError` → log + continue, so a stamping failure never turns a valid ingest/auth into a 500. No throttle (stamp-always, one indexed UPDATE by PK) — S4 can add one if it becomes hot. S4 surfaces these `last_used_at` values in usage endpoints.
- **Test-fixture note (S2/S3/S4):** the end-user self-read is now project-scoped, so `_seed_feedback` rows that must be readable through `/api/*` need `project_id=str(configured_project_credential.project_id)`. `tests/test_user_feedback_api.py::_seed_feedback` gained an optional `project_id` param; reuse that pattern. Legacy NULL-project rows fall out of any project-scoped read.

### P3.S2 outcomes — project-scoped `/api/*` review + manage landed (S3/S4 mirror these)

- **New module `src/vocky/project_feedback_api.py`**, routes under the prefix
  **`/api/project/feedback`** (distinct from the end-user self-read `GET /api/feedback`,
  no collision), wired into `create_app()` in `app.py` and guarded automatically by the
  existing `ProjectCredentialAuthMiddleware` (path `/api/…`). Verbs ported from
  `admin_api.py`: list (filters + keyset paging) / get-one (+comments+attachments) /
  PATCH review fields / DELETE / operator comments add+list / attachment download.
- **`_load_project_feedback(feedback_id, project_id) -> record | None` + 404-on-cross-project
  convention (S3/S4 mirror it):** loads via `get_feedback_event`, returns the record only
  if `record.project_id == project_id`, else `None` → **404 (never 403)** so cross-project
  existence never leaks (matches D-P2-5). Used in get/patch/delete/comments/attachment; for
  mutating ops the ownership check runs before the mutation / `get_admin_attachment`
  linkage read. List **forces** `query.filters.project_id = credential.project_id` (overrides
  any caller value), relying on the S1 `_apply_query_filters` hook (no repository change
  needed in S2).
- **`serialize_record` now lives in `src/vocky/tools/query_feedback_common.py`** (lifted out
  of `admin_api.py`, which now imports it; its local copy + unused `FeedbackEventRecord`
  import were removed). **S3's cross-project read should reuse this shared serializer.**
  Output is unchanged and carries **no `project_id` field** (the caller knows its own
  project) — if S3's `/app/*` cross-project read needs to surface which project a record
  belongs to, it must add that itself (e.g. a wrapping key) rather than change the shared
  serializer.
- **Tests:** `tests/test_project_feedback_api.py` mints a second project+credential under
  the same tenant (`_mint_project_credential` via `get_accounts_service()`) to prove
  isolation; seeds feedback rows with `project_id` via raw SQL. Reuse this second-credential
  pattern for S3/S4 cross-project tests. `uv run pytest tests/test_project_feedback_api.py
  tests/test_admin_api.py` = 21 passed; full suite 160 passed.

### P3.S3 outcomes — `/app/*` cross-project read + multilingual search landed (S4 mirrors these)

- **Search mechanism (final, D-P3-4): `pg_trgm` trigram GIN over an immutable
  concatenated expression + case-insensitive substring (`ILIKE`) predicate.**
  Confirmed `pg_trgm` is available (v1.6) and `CREATE EXTENSION` succeeds on the
  target Postgres — so **not blocked**. Predicate = SQLAlchemy
  `icontains(q, autoescape=True)` over
  `coalesce(message,'') || ' ' || coalesce(comment,'') || ' ' || coalesce(target_text,'') || ' ' || coalesce(trigger_message,'')`
  (renders `<expr> ILIKE '%'||q||'%' ESCAPE '/'`). **No `to_tsvector('english',…)`.**
  The expression is built once in
  `vocky.feedback.repository._feedback_search_target()` and the migration's raw
  DDL mirrors it byte-for-byte; `||`/`coalesce` are immutable (STABLE
  `concat`/`concat_ws` would be invalid for an expression index). `EXPLAIN`
  (seqscan off) confirms the planner uses `Bitmap Index Scan on
  ix_feedback_events_search_trgm`. Search is a **filter, newest-first** — it
  composes with the existing keyset paging; `list_feedback` is unchanged.
- **New migration `20260716_1600`** (`add_feedback_search_index`,
  `down_revision = "20260716_1500"`, now head). `upgrade()`:
  `CREATE EXTENSION IF NOT EXISTS pg_trgm` + create GIN index
  `ix_feedback_events_search_trgm` via raw `op.execute`. `downgrade()` drops the
  index only (leaves the extension). **Any later P3 migration must now chain
  `down_revision = "20260716_1600"`.** Index is not modeled in `__table_args__`
  (migration is source of truth). `tests/test_persistence.py` head pin + index
  list updated accordingly.
- **Read-model hook additions (S4 reuses):** `FeedbackQueryFilters` gained
  `project_ids: tuple[UUID,...] | None` (→ `project_id.in_(...)`) and
  `search: str | None` (→ the `icontains` predicate). Purely additive in
  `_apply_query_filters`; S2's single-project `project_id` filter is untouched.
  **Short-circuit convention:** an empty project set is handled in the handler
  (return an empty page) — do not pass an empty tuple through to a query.
- **New surface `src/vocky/app_feedback_api.py`, routes under `/app/feedback`**
  (read + search only; management stays on S2's `/api/project/feedback`), wired
  into `create_app()` after `*app_api_routes` (outside both `/api/*`
  middlewares, guarded per-handler by `require_user`; the app-wide `AuthError`
  handler renders 401). Verbs: `GET /app/feedback` (cross-project list/search,
  `?q` + optional `?project_id` narrow + standard filters + keyset paging),
  `GET /app/feedback/{id}` (+comments+attachments),
  `GET /app/feedback/{id}/attachments/{aid}` (download).
- **Tenant-project scoping + 404-on-cross-tenant (S4 mirrors):** every handler
  resolves the caller's project set via
  `get_accounts_service().list_projects_for_tenant(ctx.tenant.id)`; feedback
  outside that set (incl. legacy NULL-project rows) → **404 (never 403)** via
  `_load_scoped_feedback`. `?project_id` narrowing validates membership
  (malformed → 400, not-owned/unknown → 404). **Serialization:** reuse the
  shared `serialize_record` **augmented with `project_id`** (`_serialize_app_record`)
  — the `/app/*` caller has many projects, so records must name their project
  (contrast S2, which omits it). This is the additive extension the S2 note
  anticipated; the shared serializer was **not** changed.
- **Tests:** `tests/test_app_feedback_api.py` (terse) proves cross-project
  aggregation + paging, the **Korean** search case (`?q=결제` matches both bare
  and 조사-attached `결제를`, across two projects), English substring, project_id
  narrowing, second-tenant isolation (404), and 401 without a token. Full suite
  163 passed (was 160). Reuse the "2 projects via `POST /app/projects` + raw-SQL
  `project_id` seed + second signed-up tenant" pattern for S4 `/app/*` tests.

### P3.S4 outcomes — usage monitoring (derived + last-used) landed (final middle slice)

- **New module `src/vocky/usage_api.py`**, three read-only usage endpoints, all
  **pure reuse** of `get_feedback_metrics` scoped via the S1/S3
  `_apply_query_filters` chokepoint — **no repository change, no new query, no
  migration, no new tables** (honors D-P3-5, operational visibility not billing):
  - `GET /app/usage` (session/`require_user`) — whole-tenant capture volume
    across `list_projects_for_tenant(ctx.tenant.id)` (set as
    `FeedbackQueryFilters.project_ids`) + a light `projects:[{id,name,created_at}]`
    list. **Empty tenant short-circuits to zeroed metrics** (never queries an
    empty id set — the S3 convention), reusing `serialize_metrics(_zeroed_metrics(), query)`.
  - `GET /app/projects/{project_id}/usage` (session) — one project's volume
    (scoped by `project_id` via `_load_scoped_project`, 404 cross-tenant) +
    `credentials:[serialize_credential]`.
  - `GET /api/project/usage` (project `vk_` key via `get_request_credential`,
    auto-guarded by `ProjectCredentialAuthMiddleware`) — the credential's project
    volume + its credentials.
- **Window:** `_resolve_usage_window` reuses `parse_timestamp` +
  `validate_time_window`; **defaults to the last 30 days** (`utc_now()`-anchored)
  when both bounds omitted, fills the missing bound when only one given.
- **Surfaces the S1 `last_used_at` stamp:** the per-project surfaces return the
  project's credentials via the shared `serialize_credential`, which carries
  `last_used_at` (stamped best-effort by the ingest middleware in S1).
- **Metrics serializers NOT lifted:** `serialize_metrics` is **imported from
  `admin_api`** (matches the established cross-module pattern — `app_feedback_api`
  / `project_feedback_api` already import helpers from `admin_api`), rather than
  lifted into `tools/query_feedback_common.py`. Lower churn, admin metrics
  untouched by construction. If a future slice wants them shared, the lift is
  still available.
- **Wiring:** `*usage_routes` spliced into `create_app()` after
  `*app_feedback_routes`; no route-order collision (the `/usage` suffix
  distinguishes the `/app/projects/{id}/usage` path; `/api/project/usage` is
  distinct from `/api/project/feedback/...`).
- **Tests:** `tests/test_usage_api.py` (terse) — tenant aggregate across 2
  projects with the correct liked/disliked/unrated split + second-tenant
  isolation + empty-tenant zeroed short-circuit; per-project drill-down + 404 on
  a cross-tenant project id + `last_used_at` surfaced; `/api/project/usage`
  scoped to the credential's project; default 30-day window vs explicit window;
  401 on all three surfaces. `uv run pytest tests/test_usage_api.py
  tests/test_admin_api.py` = 22 passed; full suite 168 passed (was 163).

## Doc impact

Running list the phase REVIEW consolidates into new durable-doc versions (one version per doc, covering the whole phase):

- `product.md` — flip the "broad public REST review/query/management" **non-goal**; add project-scoped feedback API v2 + cross-project search + usage monitoring to the surface roles.
- `api.md` — new `/api/*` project-scoped review+manage endpoints and `/app/*` read/search/usage endpoints.
- `architecture.md` — project scoping on feedback, the scope-threading, the search subsystem.
- `data.md` — `feedback_events.project_id` + the search index + the P3 migration(s).
- `security.md` — project-scoped authz on reads; the credential read/manage surface.
- `decisions.md` — D-P3-1…6.
- `experience.md` — how to read/search/manage feedback via the new API.

_Landed changes (for the review to consolidate):_

- **P3.S1 → `data.md`:** `feedback_events` gains nullable `project_id` FK → `projects.id` (CASCADE) + `ix_feedback_events_project_id`; migration `20260716_1500` (chained on `20260715_1200`). Capture stamps `project_id` from the authenticating credential; legacy rows stay NULL (pre-MVP, no backfill).
- **P3.S1 → `security.md` / `architecture.md`:** ingest middleware now threads the resolved per-project credential onto the ASGI scope (`vocky.project_credential`) and best-effort stamps credential + auth-token `last_used_at`; the `GET /api/feedback` end-user self-read is now additionally project-scoped by the credential's project (defense in depth, D-P3-6).
- **P3.S2 → `api.md` / `product.md` / `experience.md` (also `architecture.md` / `security.md`):** new project-credential-authed `/api/project/feedback` review+manage endpoints — list (filters + keyset paging) / get-one (+comments+attachments) / PATCH review fields / DELETE / operator comments add+list / attachment download — scoped to the credential's project, returning 404 (never 403) on any cross-project id. External service admin panels can now read+manage their own project's feedback directly by API (`vk_` key), not just capture. No schema change; `serialize_record` is now shared in `tools/query_feedback_common.py`.
- **P3.S4 → `api.md`:** new read-only usage endpoints — `GET /app/usage` (session, whole-tenant capture volume across all the caller's projects + a light project list), `GET /app/projects/{project_id}/usage` (session, one project's volume + its credentials surfacing `last_used_at`; 404 on cross-tenant project id), `GET /api/project/usage` (project `vk_` key, the credential's project volume + its credentials). Window defaults to the last 30 days when omitted. **`product.md`:** usage monitoring is **operational-only — derived capture volume + last-used, no billing/metering** (D-P3-5). **`architecture.md`:** usage is **derived** from the existing `get_feedback_metrics` scoped by project/tenant through the shared `_apply_query_filters` chokepoint — **no new tables, queries, or migration**; the endpoints also surface the S1-wired credential/auth-token `last_used_at` stamps.
- **P3.S3 → `api.md`:** new session-authed (`require_user`) `/app/feedback` **read + search** endpoints — `GET /app/feedback` (cross-project list/search across all the caller's tenant's projects: `?q` free-text + optional `?project_id` narrow + standard filters + keyset paging), `GET /app/feedback/{id}` (+comments+attachments), `GET /app/feedback/{id}/attachments/{aid}` (download). Records carry `project_id`. Cross-tenant / not-owned ids → 404 (never 403); read-only (management stays on `/api/project/feedback`). **`architecture.md` / `data.md`:** new multilingual free-text search subsystem — case-insensitive `ILIKE` substring predicate over concatenated text columns (Korean 조사-safe + English; **no `to_tsvector('english')`**, D-P3-4) accelerated by a `pg_trgm` trigram GIN index `ix_feedback_events_search_trgm` on the immutable concatenated expression; migration `20260716_1600` (chained on `20260716_1500`, `CREATE EXTENSION pg_trgm` + index; reversible, downgrade leaves the extension). `FeedbackQueryFilters` gained `project_ids` + `search`. **`product.md`:** cross-project feedback search for signed-in users, read-only boundary (owner reads/searches across their projects; management is the project-credential surface).

## Constraints

- **Korean/multilingual search (D-P3-4):** no `to_tsvector('english', …)`; use language-agnostic trigram matching (`pg_trgm` GIN). S3 must confirm extension availability and record the final mechanism.
- **No new tables for usage (D-P3-5):** metrics are derived from existing feedback data + last-used stamps; no request-count metering.
- **No per-credential scopes (D-P3-2):** one `vk_` credential does everything for its project in the MVP.
- **No behavioral code changes here:** DECOMP creates bare slice folders only; each middle slice plans and implements at its own turn.

## Open Questions

- **Deferred-job intersection (D2).** **D2** ("scope end-user feedback read to a public-safe field subset") stays deferred — P3's new surfaces are owner/operator-scoped, so full-field exposure is appropriate. Flag the intersection for whoever revisits D2: if a public/end-user-facing read is ever added, the field-subset concern re-applies. **D1** / **D3** are unrelated to P3.
