# P10.S2 — Org-scoped enforcement, landed dark — result

**Status: done.** Every credential-derived project filter is now set-based and can never be `None`.
The org branch exists and is proven by test, but stays unreachable in production: no org-level
credential is mintable (no mint route, no `/app/credentials` surface — those are S3's), and the one
production `CreateProjectCredential` call site (`src/vocky/app_api.py:242`) still sets both scopes.

**The gate, and it is the whole point of the slice:**

> `make test` → **191 passed**, with **zero** edits to any existing test or assertion.

Not one existing pin moved — including `tests/test_project_feedback_api.py:177`
(`"project_id" not in records[0]`), which the serializer fork was specifically shaped to keep green.
That byte-for-byte pass is the cleanest available proof that the widening is purely additive, and it
is a proof that disappears once S3 turns minting on.

## What landed

### The structural decision: resolve the scope once, in the middleware

`ProjectCredentialAuthMiddleware` now stashes a **sibling** ASGI scope key beside the credential,
following the existing `PROJECT_CREDENTIAL_SCOPE_KEY` pattern exactly:

- `CREDENTIAL_PROJECT_IDS_SCOPE_KEY = "vocky.credential_project_ids"` (`src/vocky/auth.py:32`)
- `resolve_credential_project_ids(credential) -> tuple[UUID, ...]` (`:112`) — project-bound ⇒
  `(credential.project_id,)` with **no DB call**, so the hot project-bound path costs exactly what it
  cost before; org-level ⇒ `tuple(p.id for p in list_projects_for_tenant(credential.tenant_id))`.
- `get_request_project_ids(request) -> tuple[UUID, ...]` (`:243`) — mirrors `get_request_credential`'s
  shape (raises `KeyError` if the middleware did not run) and **cannot return `None`**.

The return type is the enforcement: `FeedbackQueryFilters` treats `None` as *"no filter"* rather than
*"no rows"* (`src/vocky/feedback/repository.py:562-569`), so a nullable scope fails **open** to a
global cross-tenant read. A non-`None` tuple makes that unrepresentable, and it memoizes the lookup
per request for free — the six `_load_project_feedback` sites in one handler chain would otherwise
re-resolve. No cross-request cache (revocation staleness; no cache layer in the repo to reuse).

Scope resolution **fails closed**: an `AccountsReadError` answers
`500 {"detail": "credential scope unavailable"}` and never reaches a handler. This is deliberately
*unlike* the adjacent best-effort `touch_credential_last_used`, whose swallow-and-continue semantics is
untouched.

### `project_feedback_api.py` — equality → set membership

- `_load_project_feedback(feedback_id, project_ids: tuple[UUID, ...])`; `record.project_id !=
  project_id` became `record.project_id not in project_ids`, copying
  `app_feedback_api._load_scoped_feedback`'s shape. All **six** call sites (get, patch, delete, post
  comment, list comments, attachment download) now pass `get_request_project_ids(request)`.
  `not in` is also the more correct form: `None not in (…)` is always true, so legacy NULL-project rows
  are excluded for free, where `!=` would have let a NULL-project credential *match* them.
- List route: `filters.project_ids = scope` with the empty-scope short-circuit **before** touching the
  service (copying `app_feedback_api.py:141-144`). Confirmed by reading `normalize_admin_list_query`
  (`admin_api.py:126-159`) that it does not parse `project_id`, so this assignment is the only source —
  nothing to override, and no `?project_id` narrowing to preserve. Narrowing is recorded as an option,
  not added.
- **Serializer fork, by scope shape rather than unconditionally.** `_serialize_scoped_record` returns
  `serialize_record(record)` verbatim for a project-bound credential (the "the caller knows its own
  project" premise still holds, and the pin stays green) and adds `project_id` for an org-level one
  (following `app_feedback_api._serialize_app_record`). Applied to all three record-returning handlers
  (list, get-one, patch) so the surface is internally consistent.

### `api.py` — self-read and capture

- Self-read (`:249`): `filters.project_ids = scope` + the same empty-scope guard. For a project-bound
  key a 1-element `IN` is equivalent to the old equality, NULL-row exclusion included. The D-P3-6
  defense-in-depth comment was updated to stay accurate rather than left stale.
- Capture (`:107`): the direct stamp is replaced by the shared resolver.

### Ingest project resolution (operator decision 2)

`resolve_capture_project(credential, project_name) -> UUID` lives in **`src/vocky/capture.py`** — both
writers import it with no cycle, and `app_api` is not reached into. Project-bound ⇒ the bound project
with `project_name` **ignored entirely** (not compared, not 400'd — that is what keeps existing clients
byte-for-byte); org-level ⇒ `get_or_create_project(tenant_id, name or DEFAULT_PROJECT_NAME)`. It never
returns `None`, so an org key can never enqueue an orphan row — which matters because
`capture_queue.py` round-trips `project_id` nullably and `worker.py` never re-derives it, making
**enqueue the last enforcement point**.

- `RestCaptureFeedbackInput` gained `project: str | None = None` (additive; pydantic defaults to
  `extra="ignore"`, so no existing client is affected).
- The MCP `capture_feedback` tool gained `project: str | None = None`, placed after `channel`, with
  **`ctx` still last**. FastMCP derives the schema from the signature; there is no schema object to
  update, and no test pins the tool's input schema (`tests/test_mcp_transport.py` asserts only the tool
  *name* list). It is **not** routed through `McpCaptureFeedbackInput` — the project is stamped onto the
  normalized payload after `normalize_mcp_payload`, outside caller control. The defensive `None`-request
  guard at `:99-101` is unchanged.

### `usage_api.py`

- **The pre-existing latent fail-open is defused.** `FeedbackQueryFilters(..., project_ids=project_ids
  or None)` turned an **empty tuple into no project filter at all** — i.e. a global cross-tenant read,
  safe today only because the `if not project_ids` branch happened to short-circuit first. The `or None`
  is gone; the explicit short-circuit stays, now with a comment saying why the collapse is forbidden.
  Verified safe to change: `serialize_metrics` (`admin_api.py:220-241`) echoes only the time window, not
  the project filters, so no response body moves.
- `_project_usage_response` is now scope-taking (`project_ids: tuple[UUID, ...]`), with the empty-scope
  guard; the session drill-down passes `(project.id,)` and `get_api_project_usage` passes
  `get_request_project_ids(request)`.
- The `credentials` array is the genuine fork: a project-bound scope produces today's exact payload; an
  org-level scope aggregates across its projects. Byte-for-byte for one project because the re-sort key
  `(created_at, id)` is **exactly** the repository's `ORDER BY`
  (`accounts/repository.py:203`) — checked, not assumed.

### `app_api.py`

`serialize_credential` is NULL-safe (`str(x) if x is not None else None`), so an org row renders
`project_id: null` rather than the literal string `"None"`. One edit covers both usage surfaces, which
reuse it (footgun 2 closed).

## Verification — commands and actual outcomes

| command | outcome |
|---|---|
| `make test` (before adding the new module — **the gate**) | **pass — 191 passed in 8.13s**, 0 failed, 0 existing assertions touched |
| `make test` (final, with the new module) | **pass — 196 passed in 8.53s** |
| `uv run alembic upgrade head` | **pass** — no-op; `uv run alembic current` → `20260728_1200 (head)`. Schema unchanged by this slice, as intended |
| `python3 scripts/workflow.py validate` | **pass** — `Workflow validation passed.` |
| `make smoke` (extra, not required) | **pass** — `healthz ok`; `POST /api/feedback accepted`; `GET /api/feedback ok: 1 record(s)` |

Both suite runs were green on the **first** attempt; no assertion was adjusted at any point.

`uv run ruff check` was attempted and is **not available** in this environment
(`Failed to spawn: ruff` — not a project dependency). `make test` is the repo's gate.

## Call-site enumeration (required by the plan)

`grep -rn "credential.project_id\|get_request_credential" src/vocky/` — 18 hits. Every one classified:

**Reads of `credential.project_id` — 3, all deliberate, none a filter:**

| site | why it is correct |
|---|---|
| `src/vocky/auth.py:135-136` | **the** scope resolver — the single place a nullable binding becomes a non-null tuple |
| `src/vocky/capture.py:350-351` | **the** capture resolver — the single place a nullable binding becomes a write target |
| `src/vocky/project_feedback_api.py:105` | a *serializer shape* fork (`is None` ⇒ org ⇒ include `project_id`), not a scope decision |

**Uses of `get_request_credential` — 5, none used for scoping:**

| site | what it does with the credential |
|---|---|
| `src/vocky/api.py:108` | passes it to `resolve_capture_project` |
| `src/vocky/tools/capture_feedback.py:115` | passes it to `resolve_capture_project` |
| `src/vocky/project_feedback_api.py:115,154,192` | list / get-one / patch — used **only** by `_serialize_scoped_record`; every scope decision in those handlers goes through `get_request_project_ids` |

Remaining hits are the import lines (`api.py:24`, `project_feedback_api.py:41`,
`tools/capture_feedback.py:12`), the definition (`auth.py:232`), the scope-key constant (`auth.py:32`),
the resolver call (`auth.py:204`), and two docstring mentions (`auth.py:152,253`).

**Corroborating negative check:** `grep -rn "\.project_id = \|project_id=" src/vocky/` shows the only
remaining `project_id` *assignments* in server code are the two `normalized.payload.project_id = await
resolve_capture_project(...)` writers, `app_api.py:242` (the project-bound mint), and two
repository row mappings. **`FeedbackQueryFilters.project_id` is no longer set anywhere in `src/`** —
the single-project filter path is dead in production code. Recorded in `phase.md` as a deletion option
for S3/REVIEW; deleting it here would have been a change this slice is not allowed to make.

## Tests

**No existing test was modified.** One new terse module, `tests/test_org_credential_scope.py`
(5 cases), constructing org-level credentials **directly at the service layer**
(`CreateProjectCredential(tenant_id=…, project_id=None, …)`) because there is no mint route and S2 must
not add one:

1. **An org key captures into a named project and into `"default"` when omitted** — `project: "mobile"`
   get-or-creates `mobile` (asserted absent beforehand); an omitted `project` get-or-creates `default`.
   Both enqueued payloads carry the right project id.
2. **A project-bound key is unchanged** — a `project` field in the body is neither honored nor rejected
   but **ignored**: the row lands in the bound project *and* no `mobile` project is created.
3. **An org key reads across all of its org's projects, and a second tenant stays invisible** — both
   own-org rows returned newest-first, each carrying `project_id` (the fork), and a cross-tenant id
   answers **404, never 403**, with the identical `{"detail": "feedback not found"}` body.
4. **`/api/project/usage` under an org key aggregates** its projects' credentials — and pins the S3 gap
   below.
5. **`serialize_credential` renders `project_id: null`** (not `"None"`) for an org row.

## Deviations from `plan.md`

**Three, all additive; none changes the plan's intent.**

1. **The serializer fork is applied to get-one and patch as well as list.** The plan named the
   serializer under the list route; leaving get-one/patch on the bare `serialize_record` would have made
   one surface inconsistent with itself for an org key. Project-bound output is unchanged either way.
2. **A 200-character cap on a capture-supplied `project` name**
   (`MAX_CAPTURE_PROJECT_NAME_LENGTH`, `src/vocky/capture.py`), mirroring
   `app_api.CreateProjectInput`. `projects.name` is an unbounded `Text` column and the name becomes a
   get-or-create key, so an unbounded value is a real hazard on a path that had no such guard.
   Over-long ⇒ 400 (REST) / tool error (MCP); blank or whitespace-only normalizes to the `"default"`
   fallback rather than creating a project literally named `"  "`. Unreachable for project-bound keys.
3. **A fifth test case** (`/api/project/usage` aggregation) beyond the plan's four, because the
   `credentials` fork is the plan's own "genuine fork" and would otherwise have shipped untested — and
   because pinning the current behavior turns S3's required change into a **visible test edit** rather
   than a silent one.

Everything else followed the plan as written: the middleware-resolved scope, the no-DB-call
project-bound path, fail-closed resolution, set membership at all six sites, the empty-scope
short-circuits, the `or None` removal, the scope-taking `_project_usage_response`, the NULL-safe
`serialize_credential`, `resolve_capture_project` in `capture.py` (not `app_api`), `ctx` staying last in
the MCP signature, and no mint route or `/app/credentials` surface.

## Doc impact (appended to `phase.md`, not versioned here)

No `doc-new-version` was run — `P10.REVIEW` consolidates. Five one-line notes appended: `security.md`
(the enforcement half of the trust-boundary change is real code; `:58` must be rewritten to anchor on
the middleware-resolved scope rather than the column's nullability; the `/app/usage` fail-open is
defused), `api.md` (additive `project` on REST capture and the MCP tool; `project_id` on
`/api/project/feedback` records for org keys only; `/api/project/usage` reports the whole scope;
`project_id: null` on credential payloads), `architecture.md` (the request-scoped credential project
scope as the single chokepoint; one shared ingest project resolver; enqueue is the last enforcement
point), `backend.md` (the new `auth` and `capture` primitives; set-membership `_load_project_feedback`;
scope-taking `_project_usage_response`), `product.md` (deliberately no user-visible change — the
capability is enforced before it is offered).

## S3 handoff — the one thing S3 must not forget

`/api/project/usage` builds its `credentials` array by looping `list_project_credentials(project_id)`
over the scope. **A per-project listing cannot return org-level rows (`project_id IS NULL`).** So when
S3 adds `list_org_credentials`, it **must** union those rows into `_project_usage_response` — otherwise
**an org key's own usage view omits the very keys it was minted as.** There is a `NOTE for P10.S3`
comment at the exact line in `src/vocky/usage_api.py`, and test case 4 pins the current incomplete
behavior so the fix cannot land silently. Recorded in `phase.md` too.

## Definition of done — checked

- Every credential-derived project filter is set-based and can never be `None` — yes, enumerated above.
- The org branch exists and is proven by test but is unreachable in production — yes: 5 new cases, no
  mint route, one production mint call site and it is project-bound.
- Project-bound behavior is byte-for-byte identical, and the full existing suite proves it — yes,
  191/191 with zero test edits.
- The `usage_api` `or None` fail-open is gone — yes.
- `result.md` + the `phase.md` notes (including the S3 usage-payload handoff) written — this file, a
  "P10.S2 landed" section, and five Doc impact lines.
