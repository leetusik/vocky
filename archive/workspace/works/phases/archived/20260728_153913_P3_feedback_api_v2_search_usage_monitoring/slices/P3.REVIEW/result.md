# P3.REVIEW — phase review result

**Verdict: `pass`.** All four slices validate together, the objective / intent / D-P3-1…6 are met, isolation and search were independently verified (not just green tests), and the seven durable docs were consolidated into new P3.REVIEW versions. One documented, non-blocking residual is noted below (recorded, not a fix slice).

## Part A — validation (all green)

| Check | Command | Result |
|---|---|---|
| Whole suite | `uv run pytest` | **168 passed** in 7.66s (matches the expected ~168; both P3 migrations run via `conftest`) |
| Head | `uv run alembic current` | `20260716_1600 (head)` |
| Full-chain reversibility | `uv run alembic downgrade 20260715_1200` then `upgrade head` | Both P3 migrations reverse cleanly: `…1600 → …1500 → 20260715_1200`, then `20260715_1200 → …1500 → …1600 (head)`. End-to-end reversible. |
| Workflow state | `python3 scripts/workflow.py validate` | Workflow validation passed |
| Config drift | `git diff fad759c..HEAD -- config.py pyproject.toml .env*` | Empty — P3 added no settings; nothing dirty. No config/env drift. |
| Source drift | `git status --short -- src/ alembic/ tests/` | None before Part C (only workflow state + the new plan.md were dirty). |

## Part B — critical review (read the code, not just the tests)

Reviewed against the Objective, `intent.md`, and D-P3-1…6. All met.

**Objective coverage.**
- S2 `/api/project/feedback` (`src/vocky/project_feedback_api.py`) — external-panel read+manage: list / get / PATCH / DELETE / comments / attachment, all scoped to the credential's project.
- S3 `/app/feedback` (`src/vocky/app_feedback_api.py`) — cross-project read + Korean-safe substring search.
- S4 usage (`src/vocky/usage_api.py`) — three derived read-only surfaces.
- Capture stamps `project_id`: `api.py::capture_feedback` sets `payload.project_id = get_request_credential(request).project_id` before enqueue; `capture_queue` carries it across Redis; `worker` unchanged.

**Isolation — airtight 404-never-403.**
- `_load_project_feedback` (S2) returns `None` (→404) unless `record.project_id == credential.project_id`; `_load_scoped_feedback` (S3) returns `None` (→404) unless `record.project_id in owned_ids`. Used in every per-feedback op; mutating ops (PATCH/DELETE/comment/attachment) run the ownership check before the mutation / `get_admin_attachment` linkage read.
- `project_credentials.project_id` is `NOT NULL` (`accounts/types.py:79/90`, `models.py:262` `Mapped[UUID]`), so the S2 list's **forced** `filters.project_id = credential.project_id` can never degrade to an unscoped read. Legacy NULL-`project_id` rows (None) never equal a real UUID, so they fall out of every scoped read.
- No injection path: `admin_api.normalize_list_query` never reads `project_id`/`project_ids`/`search` from the query string — the `/api/project` and `/app` handlers set scope authoritatively (and the S2 list overrides any caller value).
- Tightened self-read (D-P3-6): `api.py::list_user_feedback` sets `filters.project_id = get_request_credential(request).project_id`, so the list can't cross projects.

**Search (D-P3-4).** Substring `icontains(q, autoescape=True)` over the immutable concatenation built in `repository._feedback_search_target()`. **No `to_tsvector` anywhere** in `src/`/`alembic/` (only referenced in a doc comment). Independently verified on the live Postgres:
- `ix_feedback_events_search_trgm` exists as a GIN trigram index over the exact concatenated expression; `pg_trgm` v1.6 installed.
- `EXPLAIN` (seqscan off) on `… ILIKE '%결제%'` yields `Bitmap Index Scan on ix_feedback_events_search_trgm` with an `Index Cond` matching the concatenated expression byte-for-byte — the GIN index is genuinely used, and index-expression = predicate-expression. Korean matches (substring, 조사-safe).

**Best-effort stamping.** `ProjectCredentialAuthMiddleware` (`auth.py`) and `accounts/auth.py::require_user` each wrap the `last_used_at` stamp in `try/except AccountsPersistenceError` → log + continue, so a stamping failure never turns a valid ingest/auth into a 500.

**Reuse integrity.** `serialize_record` is shared from `tools/query_feedback_common.py`; Admin REST re-points to it and stays green (17 admin tests). `/api/project` omits `project_id`; `/app` augments via `_serialize_app_record` (shared serializer unchanged). `serialize_metrics` imported from `admin_api` (admin metrics untouched by construction).

**Free-SaaS invariant.** Usage is pure reuse of `get_feedback_metrics` through `_apply_query_filters` — `usage_api.py` has zero `CREATE TABLE` / model / `op.create_table`; P3's only schema change is the 6-line `feedback_events.project_id` column + its index and the search index. No metering/billing (D-P3-5 / D-P2-7).

### Non-blocking residual (recorded, not a fix slice)

The end-user attachment download `GET /api/feedback/{feedback_id}/attachments/{attachment_id}` (`api.py::download_user_feedback_attachment`) is authorized by `user_id` + `source_product` only — it is **not** additionally project-scoped, unlike its sibling list which D-P3-6 tightened. This is a documented, deliberate S1 scoping decision (S1 `result.md`), sits outside D-P3-6's stated scope (which named the self-read *list*), is consistent pre-existing behavior, and is only theoretically exploitable by a caller who already knows two unguessable server-generated UUIDs plus a colliding `(user_id, source_product)`. It does not compromise the phase's project-scoped surfaces (`/api/project/*`, `/app/*`), which are fully 404-isolated including attachments. Flagged for optional future hardening (also recorded in `architecture.md` Open Questions + `decisions.md` D-P3-6 Consequences); not a phase-failing finding.

## Part C — durable-doc consolidation (docs only; no source)

Seven new P3.REVIEW versions created (`doc-new-version` → edited the returned version file → `rebuild-docs` → `docs`), one per affected doc:

| Doc | New version |
|---|---|
| product | `v0004` — feedback is project-scoped; add Feedback API v2 read+manage, cross-project search, operational usage (no billing); flipped the broad-public-REST-management non-goal |
| api | `v0004` — `/api/project/feedback`, `/app/feedback` (incl. `?q` Korean search), usage endpoints (30-day default window); project-scoped self-read; `last_used_at` now stamped |
| architecture | `v0004` — feedback project scoping + ingest-scope threading; `pg_trgm` substring-search subsystem; derived usage; resolved the old P2/P3 boundary note |
| data | `v0003` — head `20260716_1600`; `project_id` FK+index (`…1500`); trigram GIN + `pg_trgm` (`…1600`); `last_used_at` now stamped |
| security | `v0003` — project-scoped read authz (404-never-403); single-key project read/manage; best-effort stamping; tightened self-read |
| decisions | `v0003` — recorded D-P3-1 … D-P3-6 |
| experience | `v0004` — read+manage via `vk_` on `/api/project/feedback`; search across projects via session on `/app/feedback` (Korean); usage via `/app/usage` |

`frontend` / `operations` / `qa` were **not** versioned (unaffected by P3); `backend` also unchanged. `rebuild-docs` regenerated `docs/current/*`; `validate` re-run passed. Part C touched only `docs/**` + workflow state — `git status -- src/ alembic/ tests/` is empty (no source drift).

## Deviations from plan

None material. Two doc `--summary` strings were shortened (the api one initially exceeded the OS filename limit); content is complete. No source written, no commits, no phase/slice status transitions — the orchestrator records the verdict via `review-phase`.
