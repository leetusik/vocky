# P3.S3 — `/app/*` cross-project read + multilingual search (native plan → slice-executor-high)

Read `works/phases/active/P3/phase.md` (esp. **P3.S1 outcomes** — the `_apply_query_filters` hook,
migration head `20260716_1500`; and **P3.S2 outcomes** — `serialize_record` now shared in
`tools/query_feedback_common.py`, the `_load_project_feedback`/404-on-cross convention) and `AGENTS.md`
first. This is the **highest-risk** slice: net-new Postgres search DDL + the operator's Korean
constraint + cross-tenant scoping. **Scope boundary:** `/app/*` here is **read + search only** —
management (edit/delete/comment) stays on S2's `/api/project/feedback`. Write no commits, no status
transitions, no `doc-new-version`.

## Search mechanism (D-P3-4 — Korean + English) — non-negotiable constraints

- **Predicate = case-insensitive substring match** over `message` + `comment` + `target_text` +
  `trigger_message`, via SQLAlchemy `icontains(q, autoescape=True)` (fall back to
  `.ilike("%"+escaped+"%")` if `icontains` isn't available on the built expression). Substring match is
  **Korean-safe** (matches 조사-attached forms: `결제` ∈ `결제를`) and English-safe, needs **no**
  language config, and **must not** use `to_tsvector('english', …)`. It is correct **with or without**
  an index.
- **Acceleration = `pg_trgm` trigram GIN index** (see Migration). Default: one GIN `gin_trgm_ops` index
  on the concatenated **immutable** expression `coalesce(message,'')||' '||coalesce(comment,'')||' '||
  coalesce(target_text,'')||' '||coalesce(trigger_message,'')`, with the predicate using that **same**
  expression so the planner can use it. Per-column trigram indexes + an OR'd predicate is an acceptable
  alternative **if** you verify cleaner index usage (EXPLAIN). **Confirm `pg_trgm` is creatable in the
  test Postgres; if it genuinely is not, return `blocked`** (don't silently drop it — the operator owns
  the target Postgres). Record the final mechanism in `phase.md`.
- **Search = filter, newest-first** — NOT relevance ranking. It composes with the existing keyset
  (`ingested_at`, `id`) paging unchanged.

## Read-layer (shared hook — S1/S2 reuse the same file)

- `src/vocky/feedback/types.py` `FeedbackQueryFilters`: add `project_ids: tuple[UUID, ...] | None` and
  `search: str | None`.
- `src/vocky/feedback/repository.py` `_apply_query_filters` (525-567): add
  `if filters.project_ids is not None: statement = statement.where(FeedbackEventModel.project_id
  .in_(filters.project_ids))` and the `search` predicate on the concatenated expression. `list_feedback`
  (381-421) is unchanged (paging/ordering compose already).

## New surface — `src/vocky/app_feedback_api.py` (routes under `/app/feedback`)

Mirror `app_api.py`: every handler `ctx = await require_user(request)`; resolve the tenant's projects
via `get_accounts_service().list_projects_for_tenant(ctx.tenant.id)`; scope to that project-id set;
**404 (never 403)** on any feedback outside it.

| Method | Path | Behavior |
|---|---|---|
| GET | `/app/feedback` | Cross-project list/search. Query: `q`, optional `project_id` (must be one of the caller's projects, else 404/400), the standard filters (feedback_value, channel, target_type, trigger_type, source_product, source_integration, conversation_id, session_id, user_id, tag, start/end_ingested_at), `limit`, `cursor`. **Empty project set → empty page** (short-circuit before querying). |
| GET | `/app/feedback/{feedback_id}` | Get one (+ comments + attachment metadata) iff its `project_id` ∈ tenant set, else 404. |
| GET | `/app/feedback/{feedback_id}/attachments/{attachment_id}` | Download; same scope (404 else) → `get_admin_attachment` + stream (`X-Content-Type-Options: nosniff`). |

- **Serialization:** reuse the shared `serialize_record` **augmented with `project_id`**
  (`{**serialize_record(r), "project_id": str(r.project_id) if r.project_id else None}`) — the user has
  many projects. Comments via `serialize_comment`; attachments via `serialize_attachment` with url
  `/app/feedback/{id}/attachments/{aid}`.
- **Normalization:** reuse the shared `query_feedback_common.py` normalizers; add a small `q` normalizer
  (trim; blank→None). Resolve `project_ids` in the handler (async), set on the filters; a `?project_id`
  narrow → validate membership then set `project_ids=(that,)`.
- **Wiring:** `from vocky.app_feedback_api import routes as app_feedback_routes`; splice
  `*app_feedback_routes` into `create_app()` (`app.py`) after `*app_api_routes`. `/app/*` is outside
  both middlewares — guarded per-handler by `require_user` (the app-wide `AuthError` handler renders 401).

## Migration

`alembic/versions/20260716_<hhmm>_add_feedback_search_index.py`, `down_revision = "20260716_1500"`.
`upgrade()`: `op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")` + `op.execute(<CREATE INDEX
ix_feedback_events_search_trgm ON feedback_events USING gin ((<concatenated expr>) gin_trgm_ops)>)`.
`downgrade()`: `DROP INDEX ix_feedback_events_search_trgm` (leave the extension). Create the index via
raw `op.execute`; do **not** model it in `__table_args__` (the migration is source of truth). Update
`tests/test_persistence.py`'s expected `feedback_events` index list (add `ix_feedback_events_search_trgm`,
sorted). It chains onto S1's head `20260716_1500`.

## Tests — `tests/test_app_feedback_api.py` (terse; the Korean case is required)

Session token via `POST /auth/signup` (the `test_app_api.py` pattern). Create 2 projects + credentials
for the tenant; seed feedback in both with `project_id` (raw SQL under `get_engine().begin()`):

- `GET /app/feedback` returns feedback from **both** projects; paging cursor works.
- **`?q=<Korean>`**: seed `message="결제 오류가 있어요"`, `?q=결제` → hit; assert `결제` also matches a
  `결제를…` row (particle case); an unrelated term → no hit. **`?q=<English>`** → matches.
- `?project_id=<own>` narrows; `?project_id=<not-owned>` → 404.
- A **second tenant's** feedback is never returned; get-one on it → 404.
- Missing session token → 401.

## Verify before returning

- `uv run alembic upgrade head` (confirm `pg_trgm` + index create — if `CREATE EXTENSION` fails,
  **`blocked`**), then `downgrade -1` + re-upgrade (reversibility).
- `uv run pytest tests/test_app_feedback_api.py tests/test_persistence.py` (real Postgres). Optionally
  full `uv run pytest`.

## result.md + phase.md notes; verdict

Write a free-form `result.md`. Append to `phase.md`: the **final chosen search mechanism** (exact index
+ predicate), the new migration revision id, the `/app/feedback` read/search surface + its
tenant-project scoping + read-only boundary, the `FeedbackQueryFilters.search`/`project_ids` additions,
and one **Doc impact** line (`api.md`: `/app/feedback` read/search; `architecture.md`/`data.md`: the
`pg_trgm` search subsystem + index + migration; `product.md`: cross-project search + the read-only
boundary). No `doc-new-version`. Return `done` on green verification, `blocked` if `pg_trgm`/the DB
can't run. (You are the top tier — do not `escalate`; if genuinely stuck, `blocked` with findings.)
