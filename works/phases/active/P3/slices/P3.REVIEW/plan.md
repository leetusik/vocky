# P3.REVIEW — phase review + durable-doc consolidation (native plan → slice-executor-high)

You are reviewing phase **P3 — Feedback API v2, Search & Usage Monitoring** in a fresh context (an
independent read). Read `works/phases/active/P3/phase.md` in full (Objective, Findings & Notes /
D-P3-1…6, the per-slice **outcomes**, and the **Doc impact** + **Landed changes** lists),
`works/phases/active/P3/intent.md`, `AGENTS.md`, and the four slices' `result.md`. Then do the three
parts below. **You may run `doc-new-version` (this is the review slice) but write NO source, make NO
commits, and do NOT transition phase/slice status** — the orchestrator runs `review-phase`.

## Part A — Validate all four slices together

- `uv run pytest` — the whole suite at once (expect ~168 green); this runs both P3 migrations via
  `conftest` and exercises every slice's tests.
- `uv run alembic upgrade head` (confirm head **`20260716_1600`**), then `uv run alembic downgrade
  20260715_1200` and back up to head — prove the full P3 chain (`…_1500` project_id, `…_1600` search
  index + `pg_trgm`) is reversible end-to-end.
- `python3 scripts/workflow.py validate` — workflow state integrity.
- Confirm no `.env`/config drift (P3 added no settings) and no stray uncommitted source.
- Any failure here ⇒ the verdict is **not** `pass`.

## Part B — Critical review (be genuinely adversarial; read the code, not just green tests)

Review against the Objective, `intent.md`, the docs, and **D-P3-1…6**. Check:
- **Objective coverage:** S2 `/api/project/feedback` (external-panel read+manage), S3 `/app/feedback`
  (cross-project search incl. **Korean**), S4 usage; capture stamps `project_id`.
- **Isolation airtight & consistent:** every project/tenant-scoped op answers **404 (never 403)** on a
  foreign id (`_load_project_feedback` in S2, `_load_scoped_feedback` in S3); legacy NULL-`project_id`
  rows fall out of scoped reads; the tightened `GET /api/feedback` self-read (D-P3-6) can't cross
  projects. Hunt for any leak or mis-scope.
- **Search (D-P3-4):** substring `ILIKE`/`icontains`, **no** `to_tsvector('english')`; index expression
  matches the predicate expression (GIN index actually used); Korean + 조사-attached forms match;
  `autoescape` safe.
- **Best-effort stamping:** a `last_used_at` failure never turns a valid ingest/auth into a 500.
- **Reuse integrity:** shared `serialize_record` / `_apply_query_filters` used consistently; admin REST
  unchanged; no divergent serializers.
- **Free-SaaS invariant:** usage is derived, no new tables/metering (D-P2-7/D-P3-5).

Issues found ⇒ **do not** consolidate docs; return `changes_requested` with file-anchored findings + a
proposed `P3.Fn` fix-slice list. Env/DB blocker ⇒ `blocked`.

## Part C — On a PASS only: consolidate the seven durable docs (docs only, never source)

For each doc: `python3 scripts/workflow.py doc-new-version --doc <name> --summary "…" --source
P3.REVIEW`, then write the **complete** updated durable content into the new
`docs/versions/<name>/vNNNN_*.md` (carry the current version forward + apply the P3 delta — never
hand-edit `docs/current/*` or old versions). After all are written, `python3 scripts/workflow.py
rebuild-docs` then `python3 scripts/workflow.py docs` to verify. Per-doc P3 delta (source: `phase.md`
Doc impact + Landed changes):

- **product.md** — flip the "broad public REST review/query/management" **non-goal**; add project-scoped
  Feedback API v2 (`/api/project/feedback`), cross-project search (`/app/feedback`), usage monitoring
  (operational only, **no billing/metering**). Feedback is now project-scoped.
- **api.md** — `/api/project/feedback` (list/get/PATCH/DELETE/comments/attachment, project-credential
  authed, 404-on-cross-project); `/app/feedback` (session; list/search `?q`+`?project_id`+filters+keyset,
  get-one, attachment download); usage `/app/usage`, `/app/projects/{id}/usage`, `/api/project/usage`
  (30-day default window); the tightened project-scoped `GET /api/feedback`.
- **architecture.md** — feedback `project_id` scoping + ingest-middleware→ASGI-scope threading
  (`vocky.project_credential`/`get_request_credential`); the `pg_trgm` substring-search subsystem
  (filter, newest-first); usage derived from `get_feedback_metrics`; resolve the old P2/P3 boundary note.
- **data.md** — head now **`20260716_1600`**; `feedback_events.project_id` FK CASCADE +
  `ix_feedback_events_project_id` (migration `20260716_1500`); `ix_feedback_events_search_trgm` GIN +
  `pg_trgm` (migration `20260716_1600`); `last_used_at` now stamped on credentials + auth tokens.
- **security.md** — project-scoped read authz (404-never-403 on `/api/project/*` + `/app/feedback`); the
  credential read/manage surface (one `vk_` key does capture + project read/manage, no per-credential
  scopes); best-effort `last_used_at` stamping; tightened self-read.
- **decisions.md** — record **D-P3-1 … D-P3-6** verbatim from `phase.md`.
- **experience.md** — extend the integration guide: read+manage your project's feedback with the `vk_`
  key on `/api/project/feedback`; search across your projects via the session on `/app/feedback` (Korean
  works); view usage via `/app/usage`.

Do **not** version `frontend.md` / `operations.md` / `qa.md` (unaffected by P3).

## Before returning `pass`

- Re-run `python3 scripts/workflow.py validate` and `python3 scripts/workflow.py docs` — all seven docs
  show a new P3.REVIEW version and `docs/current/*` regenerated.
- Confirm **only `docs/**` + workflow state changed** in Part C (no source).

## Write result.md + return the verdict

Write a free-form `result.md` (validation output, review findings, docs versioned). Return
`review_verdict` = `pass` (all green, no material findings, all seven docs versioned+rebuilt) /
`changes_requested` (findings + proposed `P3.Fn` fixes; docs untouched) / `blocked` (env/DB). No commit,
no status transitions — the orchestrator records the verdict with `review-phase`.
