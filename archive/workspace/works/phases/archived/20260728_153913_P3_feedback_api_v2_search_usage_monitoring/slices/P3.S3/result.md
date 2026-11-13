# P3.S3 result — `/app/feedback` cross-project read + multilingual search

**Status: done.** `pg_trgm` is available and creatable on the target Postgres, so
the `blocked` path was not taken.

## What landed

### Search mechanism (D-P3-4) — final chosen mechanism

- **Predicate:** case-insensitive substring match via SQLAlchemy
  `icontains(q, autoescape=True)` over the **immutable** concatenated expression
  `coalesce(message,'') || ' ' || coalesce(comment,'') || ' ' || coalesce(target_text,'') || ' ' || coalesce(trigger_message,'')`.
  Renders as `<expr> ILIKE '%'||q||'%' ESCAPE '/'`. **No `to_tsvector('english', …)`**.
  Language-agnostic: matches Korean 조사-attached forms (`결제` ⊂ `결제를`) and
  English uniformly. Correct with or without the index.
- **Acceleration:** a single **`pg_trgm` trigram GIN index**
  `ix_feedback_events_search_trgm` over that *same* expression (default plan
  option, not per-column). The expression is built once in
  `vocky.feedback.repository._feedback_search_target()` (the predicate) and
  mirrored in the migration's raw DDL (`_SEARCH_EXPR`). `||`/`coalesce` are
  immutable (unlike STABLE `concat`/`concat_ws`), so the expression index is
  valid.
- **Verified index usage:** `EXPLAIN` with `enable_seqscan=off` on the exact
  compiled predicate yields `Bitmap Index Scan on ix_feedback_events_search_trgm`
  with the `Index Cond` matching the concatenated expression — the planner can
  and does use the index. (At test-table scale it seq-scans, which is correct
  and expected.)
- Search is a **filter, newest-first** — it composes unchanged with the existing
  `(ingested_at, id)` keyset paging; `list_feedback` was not touched.

### Migration

- **New revision `20260716_1600`** (`add_feedback_search_index`,
  `down_revision = "20260716_1500"`, now head). `upgrade()` runs
  `CREATE EXTENSION IF NOT EXISTS pg_trgm` then creates the trigram GIN index via
  raw `op.execute`. `downgrade()` drops the index only and **leaves the
  extension**. The index is **not** modeled in `__table_args__` — the migration
  is the source of truth. Verified fully reversible (downgrade -1 → re-upgrade
  head).

### Read-layer hook (shared `_apply_query_filters`)

- `FeedbackQueryFilters` gained `project_ids: tuple[UUID, ...] | None` and
  `search: str | None`. `_apply_query_filters` now applies
  `project_id.in_(project_ids)` and the `icontains` search predicate. Both are
  additive; the existing `project_id` (single) filter and everything else are
  unchanged, so S2's `/api/*` path is unaffected.

### New surface — `src/vocky/app_feedback_api.py` (read + search only)

- Session-authed (`require_user`) routes, wired into `create_app()` after
  `*app_api_routes` (outside both `/api/*` middlewares; per-handler guarded):
  - `GET /app/feedback` — cross-project list/search across all the caller's
    tenant's projects. Query: `q`, optional `project_id` narrowing, plus the
    standard filters/limit/cursor (reuses `admin_api.normalize_list_query`).
    **Empty project set → empty page** (short-circuits before querying).
  - `GET /app/feedback/{feedback_id}` — get one (+comments+attachments).
  - `GET /app/feedback/{feedback_id}/attachments/{attachment_id}` — download
    (`get_admin_attachment` + stream, `X-Content-Type-Options: nosniff`).
- **Scoping:** projects resolved via
  `get_accounts_service().list_projects_for_tenant(ctx.tenant.id)`; any feedback
  outside that id set (including legacy NULL-project rows) answers **404 (never
  403)**. `?project_id` narrowing validates membership: malformed → 400,
  not-owned/unknown → 404.
- **Serialization:** reuses shared `serialize_record` **augmented with
  `project_id`** (via `_serialize_app_record`), since the caller has many
  projects; comments via `serialize_comment`; attachments via
  `serialize_attachment` with `/app/feedback/{id}/attachments/{aid}` urls.
- **Management stays out of scope** — edit/delete/comment remain on S2's
  `/api/project/feedback`.

## Validation (all green)

| Command | Result |
|---|---|
| `uv run alembic upgrade head` | OK — `20260716_1500 -> 20260716_1600`; `pg_trgm` + `ix_feedback_events_search_trgm` created |
| `EXPLAIN` (seqscan off) on the search predicate | `Bitmap Index Scan on ix_feedback_events_search_trgm` — index usable |
| `uv run alembic downgrade -1` then `uv run alembic upgrade head` | OK — index dropped (extension kept) then re-created; reversible |
| `uv run pytest tests/test_app_feedback_api.py tests/test_persistence.py` | 11 passed |
| `uv run pytest` (full suite) | 163 passed |
| `python3 scripts/workflow.py validate` | passed |

`tests/test_app_feedback_api.py` covers: cross-project aggregation (newest-first,
each record tagged with `project_id`) + keyset paging; the **Korean** case
(`?q=결제` matches both `결제 오류가 있어요` and the particle-attached
`결제를 못 했습니다`, across two projects; unrelated term → empty); English
substring match; `?project_id` narrowing (owned → narrows; not-owned/unknown →
404; malformed → 400); a second tenant's feedback never returned + get-one on it
→ 404; and 401 without a session token. `tests/test_persistence.py`'s head pin
(`20260716_1600`) and index list (`ix_feedback_events_search_trgm`, sorted) were
updated.

## Deviations from plan

- **`q` normalizer:** the plan called for "a small `q` normalizer (trim;
  blank→None)"; the existing shared `normalize_optional_text` already does
  exactly that, so it was reused inline rather than adding a near-duplicate
  helper.
- **Test setup:** the plan mentioned creating "2 projects + credentials" for the
  seed. The `/app/feedback` surface is session-authed and read-only, so ingest
  **credentials add nothing** to these tests — the test creates 2 projects (via
  `POST /app/projects`) and seeds feedback with `project_id` directly, omitting
  the unused credentials. Cross-tenant isolation is proven with a genuine second
  signed-up tenant rather than a second credential.

No other deviations.
