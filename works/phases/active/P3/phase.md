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

## Doc impact

Running list the phase REVIEW consolidates into new durable-doc versions (one version per doc, covering the whole phase):

- `product.md` — flip the "broad public REST review/query/management" **non-goal**; add project-scoped feedback API v2 + cross-project search + usage monitoring to the surface roles.
- `api.md` — new `/api/*` project-scoped review+manage endpoints and `/app/*` read/search/usage endpoints.
- `architecture.md` — project scoping on feedback, the scope-threading, the search subsystem.
- `data.md` — `feedback_events.project_id` + the search index + the P3 migration(s).
- `security.md` — project-scoped authz on reads; the credential read/manage surface.
- `decisions.md` — D-P3-1…6.
- `experience.md` — how to read/search/manage feedback via the new API.

## Constraints

- **Korean/multilingual search (D-P3-4):** no `to_tsvector('english', …)`; use language-agnostic trigram matching (`pg_trgm` GIN). S3 must confirm extension availability and record the final mechanism.
- **No new tables for usage (D-P3-5):** metrics are derived from existing feedback data + last-used stamps; no request-count metering.
- **No per-credential scopes (D-P3-2):** one `vk_` credential does everything for its project in the MVP.
- **No behavioral code changes here:** DECOMP creates bare slice folders only; each middle slice plans and implements at its own turn.

## Open Questions

- **Deferred-job intersection (D2).** **D2** ("scope end-user feedback read to a public-safe field subset") stays deferred — P3's new surfaces are owner/operator-scoped, so full-field exposure is appropriate. Flag the intersection for whoever revisits D2: if a public/end-user-facing read is ever added, the field-subset concern re-applies. **D1** / **D3** are unrelated to P3.
