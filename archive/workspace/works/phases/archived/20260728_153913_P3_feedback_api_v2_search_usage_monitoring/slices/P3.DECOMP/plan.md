# P3.DECOMP — plan (orchestrator → slice-executor-high)

You are executing the **decomposition** slice for phase **P3 — Feedback API v2, Search & Usage
Monitoring**. Your job is to **create P3's four middle-slice folders** (bare — `slice.json` only, no
`plan.md`) and **seed `phase.md`** with the breakdown, decisions, and doc-impact notes. **Do not
write any application code, do not pre-fill any middle slice's `plan.md`, do not run
`doc-new-version`, do not commit, and do not transition any slice/phase status.** The orchestrator
owns all commits and status transitions and trusts your verdict.

Read `works/phases/active/P3/phase.md` and `works/phases/active/P3/intent.md` first for context. All
key decisions below are **operator-approved** (asked and confirmed at the DECOMP gate) — instantiate
them, don't re-litigate.

## Step 1 — Create the four middle slices (exact commands)

Run these verbatim (`python3 scripts/workflow.py …`). Orders 1–4 sit between DECOMP (0) and REVIEW
(9999). `--risk` sets the executor tier for each slice — it is deliberate; do not change it.

```
python3 scripts/workflow.py new-slice --phase P3 --slice P3.S1 \
  --name "Project-scope foundation: project_id on feedback + capture threading + last_used stamps" \
  --kind implementation --risk medium --order 1

python3 scripts/workflow.py new-slice --phase P3 --slice P3.S2 \
  --name "/api project-scoped feedback review + manage (project-credential authed)" \
  --kind implementation --risk medium --order 2 --depends-on P3.S1

python3 scripts/workflow.py new-slice --phase P3 --slice P3.S3 \
  --name "/app cross-project feedback read + multilingual Postgres search" \
  --kind implementation --risk high --order 3 --depends-on P3.S1

python3 scripts/workflow.py new-slice --phase P3 --slice P3.S4 \
  --name "Usage monitoring: per-tenant/project derived metrics + surfaced last-used" \
  --kind implementation --risk medium --order 4 --depends-on P3.S1
```

After creating them, run `python3 scripts/workflow.py validate` and confirm all four folders exist
with only `slice.json` (no `plan.md`). Do **not** create `plan.md` for them.

## Step 2 — Seed `works/phases/active/P3/phase.md`

Fill the existing empty sections (keep the `_Intent: see intent.md_` line and Objective as-is).
Write these into `phase.md`:

### Under `## Decomposition`

Record the four-slice breakdown with one-line rationale each, plus the dependency shape (S2/S3/S4 all
depend on S1; S1 is the foundation). Note that the executor of S2 or S3 **may split** its slice if it
proves too large (e.g. S3 → migration+predicate vs `/app` endpoints), recording the rationale here.

- **P3.S1 — Project-scope foundation** (medium): nullable `project_id` FK on `feedback_events`
  (+ index), chained on head `20260715_1200`; model field; middleware threads the resolved
  `credential.project_id` (+ credential id) onto the ASGI scope; capture stamps `project_id` end-to-end
  (handler → `CreateFeedbackEvent` → `capture_queue` serialize/deserialize → worker → repository);
  wire the never-called `last_used_at` stamps; tighten the end-user self-read to also scope by project.
  Update `tests/test_persistence.py` head-pin + index list. **Everything depends on this.**
- **P3.S2 — `/api/*` project-scoped review + manage** (medium): `project_id` scoping in
  `_apply_query_filters`; project-credential-authed routes (project from scope) that port the
  `admin_api.py` verbs — list (filters+keyset paging) / get-one (+comments+attachments) / PATCH review
  fields / operator comments add+list / delete. Distinct pathing from the end-user self-read.
- **P3.S3 — `/app/*` cross-project read + multilingual search** (high): net-new Postgres search
  migration (extension + trigram GIN per the Korean constraint below); multilingual free-text `q`
  predicate; session-authed `/app/*` endpoints listing/searching across ALL the caller's tenant's
  projects (+ optional `project_id` narrowing) + get-one. Consumed by P4/P5. Riskiest slice.
- **P3.S4 — Usage monitoring** (medium): scope `get_feedback_metrics`/`summarize_feedback` per
  project/tenant; `/app/*` usage endpoints (capture volume over time by value/channel; surface
  credential last-used); optionally per-project usage on `/api/*`.

### Under `## Findings & Notes` — record D-P3-1…6 verbatim

- **D-P3-1** Feedback gains nullable `project_id` FK → `projects.id`; capture stamps it from the
  authenticating credential's project; middleware threads project scope onto the ASGI scope. Legacy
  rows stay NULL (pre-MVP, no backfill).
- **D-P3-2** "Both, full" scope: a project credential authorizes capture **and** project-scoped
  read+manage of its own project's feedback on `/api/*` (external-admin-panel path). **No per-credential
  scopes** in the MVP — one `vk_` key does everything for its project; scopes deferred.
- **D-P3-3** Cross-project read + search live on `/app/*` (session/`require_user`), scoped to the
  caller's tenant's projects; consumed by P4 dashboard and P5 CLI.
- **D-P3-4 (Korean/multilingual search constraint — operator-stated).** Feedback **may be Korean**.
  Do **NOT** use `to_tsvector('english', …)` — English stemming is wrong for Korean and Korean
  particles/조사 defeat word-token matching. Recommended mechanism: **`pg_trgm` trigram GIN**
  (language-agnostic substring/similarity; handles Korean 조사-attached forms + English uniformly),
  optionally a `simple`-config `tsvector` for ranking. **The S3 executor must confirm `pg_trgm`
  (or `pg_bigm`) availability on the target Postgres and record the final chosen mechanism here.**
- **D-P3-5** Usage = derived + last-used, **no new tables**: reuse `get_feedback_metrics`/
  `summarize_feedback` scoped per project/tenant, and wire the already-built, never-called
  `touch_credential_last_used`/`touch_auth_token_last_used`. No request-count metering (honors
  D-P2-7 free/no-billing).
- **D-P3-6** The existing `GET /api/feedback` end-user self-read additionally scopes to the
  credential's project (defense in depth), once `project_id` is threaded.

Also record the **key implementation anchors** (so downstream slice plans start grounded):
scope-threading hook `src/vocky/auth.py:98-122`; query chokepoint `feedback/repository.py:525-567`
(`_apply_query_filters`, `tags.contains([...])` at 565 is the non-equality template); verbs to port
`src/vocky/admin_api.py` (+ `feedback/service.py` already supports them); metrics precedent
`feedback/repository.py:467-523`; last_used stamps in `accounts/repository.py` (call from the
middleware + `accounts/auth.py:require_user`); capture threading via `feedback/types.py`
`CreateFeedbackEvent` + `capture_queue.py:56-175` + `worker.py`; migration head `20260715_1200`,
GIN precedent `postgresql_using="gin"`; tests use real Postgres + the `configured_project_credential`
fixture, and any new table must be appended to both TRUNCATE lists (`tests/conftest.py:142-155`).

### Add a `## Doc impact` list (for the REVIEW to consolidate)

Seed the running doc-impact list the phase REVIEW will turn into new versions:
- `product.md` — flip the "broad public REST review/query/management" **non-goal**; add project-scoped
  feedback API v2 + cross-project search + usage monitoring to the surface roles.
- `api.md` — new `/api/*` project-scoped review+manage endpoints and `/app/*` read/search/usage endpoints.
- `architecture.md` — project scoping on feedback, the scope-threading, the search subsystem.
- `data.md` — `feedback_events.project_id` + the search index + the P3 migration(s).
- `security.md` — project-scoped authz on reads; the credential read/manage surface.
- `decisions.md` — D-P3-1…6.
- `experience.md` — how to read/search/manage feedback via the new API.

### Note the deferred-job intersection

Under Notes/Open Questions: **D2** ("scope end-user feedback read to a public-safe field subset")
stays deferred — P3's new surfaces are owner/operator-scoped, so full-field exposure is appropriate;
flag the intersection for whoever revisits D2. **D1**/**D3** are unrelated to P3.

## Step 3 — Write `result.md` and return a verdict

Write a short free-form `works/phases/active/P3/slices/P3.DECOMP/result.md` summarizing what you
created (the four slices + their risks) and that `phase.md` was seeded. Return a structured verdict:
`done` if the four slices exist and `phase.md` is seeded and `validate` passes; `escalate` (this is
`slice-executor-high`, the ceiling — instead `blocked`/`needs_operator`) only if something genuinely
blocks you. Remember: no code, no middle-slice `plan.md`, no `doc-new-version`, no commit, no status
transitions.
