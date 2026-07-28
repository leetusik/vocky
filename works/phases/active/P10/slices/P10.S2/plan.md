# P10.S2 — Org-scoped enforcement, landed dark

kind `implementation` · risk **high** → `slice-executor-high` · depends `P10.S1`

## Context

S1 landed the schema: `project_credentials.tenant_id` is NOT NULL, `project_id` is nullable, and
`ProjectCredentialRecord` now carries **both** (`src/vocky/accounts/types.py`). No row has a NULL
`project_id` and there is no way to mint one — S3 adds that.

S2 makes **every consumer of the authenticating credential's project binding org-aware, before any org
key exists.** This is the phase's binding constraint (`phase.md § Constraints`):

> No slice may make an org key mintable until every credential-derived project filter is org-aware.

**Why this slice is `high` risk despite changing no observable behavior:** `FeedbackQueryFilters` treats
`None` as *"no filter"*, not *"no rows"* (`src/vocky/feedback/repository.py:555-570`). A credential that
resolves with a NULL project therefore reads **every project in every tenant**. The failure mode is a
silent cross-tenant read, not an error.

**The slice's whole point is that nothing observable changes.** No org key exists, so the entire
existing suite must pass **byte-for-byte** — identical rows, identical 404s, and identical response
*bodies*. Any diff in behavior for a project-bound key is a bug in this slice.

## The structural decision: resolve the scope once, in the middleware

Do **not** resolve the org's project set per handler. There are ten call sites across four modules and
one missed site is a silent global read.

In `src/vocky/auth.py`, `ProjectCredentialAuthMiddleware` (`:129-156`) already stashes the credential
under a namespaced ASGI scope key (`PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"`, `:21`,
`:145`) with an accessor at `:161-170`. Add a sibling, following that exact pattern:

- `CREDENTIAL_PROJECT_IDS_SCOPE_KEY = "vocky.credential_project_ids"`
- resolved immediately after the credential, in the middleware:
  - `credential.project_id is not None` → `(credential.project_id,)` — **no DB call**, so the
    project-bound path costs exactly what it costs today
  - `project_id is None` (org-level, unreachable until S3) →
    `tuple(p.id for p in await list_projects_for_tenant(credential.tenant_id))`
- accessor `get_request_project_ids(request) -> tuple[UUID, ...]`, mirroring `get_request_credential`'s
  shape (raise if the middleware did not run; **never** return `None`).

**The return type is the enforcement.** A `tuple[UUID, ...]` that cannot be `None` means no handler can
accidentally produce an unfiltered read, and it memoizes the lookup per request for free — the six
`_load_project_feedback` call sites in one handler chain would otherwise re-resolve.

No cross-request cache: revocation staleness, and this repo has no cache layer to reuse (only
`config.get_settings()`, the engine, and the Redis client). Cost is one extra indexed SELECT per
*org-scoped* request against a middleware that already does two round trips.

## Scope

### 1. `src/vocky/auth.py` — resolve and stash

As above. Keep `touch_credential_last_used`'s best-effort semantics untouched. If the project-set lookup
raises, fail **closed** (401 or 500 — not an empty scope that silently reads nothing, and never an
unscoped read).

### 2. `src/vocky/project_feedback_api.py` — equality → set membership

- `_load_project_feedback` (`:64-79`): signature takes `project_ids: tuple[UUID, ...]`;
  `record.project_id != project_id` becomes `record.project_id not in project_ids`. Update all six call
  sites (`:121` get, `:189` patch, `:218` delete, `:274` post comment, `:302` list comments, `:335`
  attachment download) to pass `get_request_project_ids(request)`.
  **`not in` is also the more correct form**: it excludes legacy NULL-`project_id` rows for free
  (`None not in (…)` is True), where `!=` would let a NULL-project credential *match* NULL-project rows.
  `src/vocky/app_feedback_api.py:108-123` is the existing precedent — copy its shape.
- List route (`:94`): `filters.project_id = credential.project_id` → `filters.project_ids = scope`, with
  the **empty-scope short-circuit before touching the service**, copying
  `src/vocky/app_feedback_api.py:141-144`: return an empty page rather than querying with an empty set.
  Note `normalize_admin_list_query` (`src/vocky/admin_api.py:126-159`) does not parse `project_id`, so
  this assignment is the only source — there is nothing to "override" and no `?project_id` narrowing to
  preserve. **Do not add narrowing in this slice**; record it as an option.
- **Serializer.** This surface uses `serialize_record`
  (`src/vocky/tools/query_feedback_common.py:153-192`), which deliberately omits `project_id` because
  "the project-scoped caller knows its own project from its credential", and
  `tests/test_project_feedback_api.py:176` pins `"project_id" not in records[0]`. An org key breaks that
  premise. Resolve it by **scope shape, not unconditionally**: a project-bound credential keeps
  `serialize_record` exactly as-is (the pin stays green); an org-level credential gets `project_id`
  added, following `src/vocky/app_feedback_api.py:57-68`
  (`{**serialize_record(record), "project_id": …}`). Document the fork in `phase.md`.

### 3. `src/vocky/api.py` — self-read and capture

- **Self-read (`:236`)**: `filters.project_id = credential.project_id` → `filters.project_ids = scope`
  with the same empty-scope guard. For a project-bound key a 1-element `IN` is byte-for-byte equivalent
  to today's equality, including its exclusion of legacy NULL rows. Keep the D-P3-6 defense-in-depth
  comment accurate.
- **Capture (`:99`)**: replace the direct stamp with the shared resolver below.

### 4. Ingest project resolution (operator decision 2)

One helper, used by both writers — put it where both can import it without a cycle (a small function in
`src/vocky/capture.py` or a new module; do **not** reach into `app_api`):

```
async def resolve_capture_project(credential, project_name: str | None) -> UUID
    project-bound  -> credential.project_id          # the name is IGNORED entirely
    org-level      -> (await get_or_create_project(
                          credential.tenant_id,
                          project_name or DEFAULT_PROJECT_NAME)).id
```

- Project-bound keys **ignore the field completely** — that is what keeps them byte-for-byte. Do not
  400 on a supplied name, do not compare it to the bound project.
- The org branch never yields `None`, so an org key can never enqueue an orphan row. This matters:
  `src/vocky/capture_queue.py:62,97-100` round-trips `project_id` nullably and
  `src/vocky/worker.py` never re-derives it, so **enqueue is the last enforcement point**.
- `RestCaptureFeedbackInput` (`src/vocky/capture.py:66-72`) gains `project: str | None = None`.
  Additive and safe — pydantic defaults to `extra="ignore"`, so no existing client is affected.
- `src/vocky/tools/capture_feedback.py`: add `project: str | None = None` to the tool signature
  (FastMCP derives the schema from the signature — there is no separate schema object). Place it near
  `source`/`channel`; **`ctx` must stay last**. Resolution replaces the stamp at `:103`, keeping the
  existing defensive `None`-request guard at `:96-101`.
  Do **not** route it through `McpCaptureFeedbackInput` — `project_id` is stamped onto the normalized
  payload after `normalize_mcp_payload`, deliberately outside caller control.

### 5. `src/vocky/usage_api.py`

- **Fix the pre-existing latent fail-open first.** `:149-172` builds
  `FeedbackQueryFilters(..., project_ids=project_ids or None)` — an empty tuple becomes `None`, i.e.
  *no project filter at all*. It is safe today only because the `if not project_ids` branch
  short-circuits before that query runs. **Drop the `or None`** so an empty tuple stays an empty tuple,
  and keep the explicit short-circuit. This is a real bug being defused, not a refactor; note it in
  `phase.md`.
- `get_api_project_usage` (`:192-202`) → `_project_usage_response(credential.project_id, …)`
  (`:107-136`) becomes scope-taking: metrics via `filters.project_ids = scope` (+ guard).
- **The `credentials` array is the genuine fork.** A project-bound credential keeps today's exact
  payload (`list_project_credentials(project_id)`). For an org-level credential, aggregate across the
  scope's projects, oldest-first. **Flag for S3:** a per-project listing cannot return org-level rows
  (`project_id IS NULL`), so when S3 adds `list_org_credentials` it must extend this response too, or an
  org key's usage view will omit the very keys it was minted as. Record this in `phase.md`.

### 6. `src/vocky/app_api.py` — NULL-safe serializer

`serialize_credential` (`:79-94`) does `str(record.project_id)` unconditionally, so an org row would
serialize the literal string `"None"`. Make it `str(x) if x is not None else None`. It is **reused** by
`src/vocky/usage_api.py:38,135`, so this one edit covers both surfaces. (Footgun 2.)

### 7. Tests

**The gate is that the existing suite passes byte-for-byte.** Do not update an existing assertion to
accommodate this slice — if one fails, the slice is wrong, not the test. The exception is a signature
change that a test constructs directly.

**Add, terse** — one small module exercising the dark path. Construct an org-level credential
**directly at the service layer** (`CreateProjectCredential(tenant_id=…, project_id=None, …)`); there is
no mint route and S2 must not add one. This is not a breach of S1's "no NULL rows" invariant — that
invariant is about production code paths, and the dark branch is exactly what needs proving. Assert:

- an org key captures into a **named** project (get-or-created on first use) and into `"default"` when
  `project` is omitted;
- an org key reads across **all** of its org's projects, and a second tenant's rows stay invisible
  (404-never-403 preserved);
- a project-bound key is **unchanged** — captures into its bound project, and a `project` field in the
  body is ignored rather than honored or rejected;
- `serialize_credential` renders `project_id: null` (not `"None"`) for an org row.

## Not this slice

`/app/credentials` and any mint path, the tenant-aware resolver work S3 owns, `?project_id` narrowing,
web, CLI, docs. **No `doc-new-version`** — append one-line **Doc impact** notes to `phase.md`.

## Verification

```bash
make test                            # the gate: every existing test green, unchanged
uv run alembic upgrade head          # schema unchanged by this slice; confirm clean
python3 scripts/workflow.py validate
```

Then verify by inspection, and record it in `result.md`: **enumerate every call site that reads
`credential.project_id`** and confirm each one now goes through `get_request_project_ids` or the capture
resolver. `grep -rn "credential.project_id\|get_request_credential" src/vocky/` — every remaining hit
must be deliberate and explained.

## Definition of done

Every credential-derived project filter is set-based and can never be `None`; the org branch exists and
is proven by test but is unreachable in production; project-bound behavior is byte-for-byte identical
and the full existing suite proves it; the `usage_api` `or None` fail-open is gone; `result.md` and the
`phase.md` notes (especially the S3 handoff about org-level credentials in the usage payload) are
written.
