# P10.S3 — Org-key mint surface — result

**Status: done. Org keys are on.** A `vk_` credential with `project_id IS NULL` can now be minted,
listed, used across every project in its org, and revoked. This is the slice that widens the trust
boundary, and it is safe only because S2 landed: every credential-derived project filter was already
set-based and resolved once in the middleware, so nothing here had to touch enforcement.

**S2's proof is cited, not re-derived** — 191/191 byte-for-byte with zero assertion edits was the
additivity proof, and it is unavailable from this slice on. What replaces it here: **201 passed** on
the first run (196 + 5 new cases), with exactly **one** existing assertion changed, and that one was
planted by S2 on purpose so this slice's fix would be visible.

## 1. The resolver — verified, not invented (plan §3)

`resolve_credential_project_ids` (`src/vocky/auth.py:112-141`) was read line by line and is
**untouched**. It already handles both branches correctly:

- project-bound ⇒ `return (credential.project_id,)` — no DB call, so the hot path costs what it cost;
- org-level ⇒ `tuple(project.id for project in list_projects_for_tenant(credential.tenant_id))`.

The middleware stashes it under `CREDENTIAL_PROJECT_IDS_SCOPE_KEY` and fails **closed** on an
`AccountsReadError`. **S3 added zero resolver logic.**

**The "vanished project ⇒ unresolvable" guard has no vocky analogue to port**, and adding one would
guard a state that cannot exist. Two independent reasons, both checked in the tree:

1. vocky's resolver **never loads a project** — a project-bound credential returns its own
   `project_id` without touching `projects` at all, so there is no "project missing" branch to be in.
2. `project_credentials.project_id` is `ON DELETE CASCADE` (`src/vocky/persistence/models.py`, and the
   `20260728_1200` migration preserves it), so deleting a project deletes its bound credentials. A
   credential pointing at a vanished project is not reachable. For an org key the question does not
   arise: it resolves through `tenant_id`, and a deleted project simply drops out of the set.

## 2. Accounts layer

`src/vocky/accounts/repository.py` + `service.py`, both plain reads:

- **`list_org_credentials(tenant_id)`** — `tenant_id = :tid AND project_id IS NULL`, ordered
  `(created_at, id)` (the house ordering, the same key `_project_usage_response` re-sorts on), revoked
  rows included like `list_project_credentials`. Disjoint from the per-project listing in both
  directions, which is what makes the usage union safe from double-counting.
- **`get_credential(credential_id)`** — a by-PK read, **unscoped by design**; the docstring says the
  caller owns the ownership check and must answer 404, never 403. Deliberately **not** modelled on
  `delete_credential`'s list-a-project-and-scan-in-Python shape: one indexed read plus an explicit
  two-clause check is O(1) and states the rule in one place. **The existing per-project route was left
  exactly as it is** — rewriting it is not this slice's job and it is still correct.

Service wrappers follow the file's existing shape (`AccountsReadError` on `SQLAlchemyError`).

## 3. The three org routes (`src/vocky/app_api.py`)

Additive beside the per-project routes, session-authed via `require_user` exactly like their
neighbours. Key generation is unchanged: `key = f"vk_{generate_opaque_token()}"`,
`token_prefix = key[:12]`, `token_hash = sha256_hex(key)`.

| route | behavior |
|---|---|
| `POST /app/credentials` | `CreateProjectCredential(tenant_id=ctx.tenant.id, project_id=None, …)` via `_parse_optional_body` + `CreateCredentialInput`. `201 {credential, key}` — the same shape as the per-project mint, plaintext once. |
| `GET /app/credentials` | `200 {credentials: [...]}` from `list_org_credentials`, oldest-first, revoked included. |
| `DELETE /app/credentials/{credential_id}` | `204`; `400` on a malformed UUID; `404 {"detail": "credential not found"}` — the per-project route's exact anti-probe wording. |

**404-never-403, tighter than it looks.** The delete guard is
`record is None or record.tenant_id != ctx.tenant.id or record.project_id is not None`. The third
clause is the one that matters: a **project-bound credential of the caller's own tenant 404s here**,
identically to another tenant's key and to an id that does not exist. So the org surface can neither
revoke nor probe a project-bound key, and `/app/projects/{id}/credentials/{cid}` remains the only way
to revoke one. Pinned by `test_org_delete_is_404_never_403_even_for_a_bound_key`, which also asserts
that none of the probes revoked anything.

## 4. The usage union — S2's handoff, closed (plan §4)

`_project_usage_response` gained a keyword-only `org_tenant_id: UUID | None = None`; when set it
extends the credential list with `list_org_credentials(org_tenant_id)` before the `(created_at, id)`
re-sort (so the union is still globally oldest-first — S2's ordering gotcha, honored).

`get_api_project_usage` passes `credential.tenant_id` **only** when `credential.project_id is None`.
That read is a *shape* test, not a filter — the project filter is still `get_request_project_ids(request)`
— and there is a comment at the line saying exactly that. The session drill-down
`/app/projects/{id}/usage` passes nothing, so **its payload is byte-for-byte unchanged**: an org key is
not one project's key and must not appear in a project's drill-down.

The `NOTE for P10.S3` comment was **replaced by the resolution**, not deleted, and the pin S2 planted
in `tests/test_org_credential_scope.py::test_org_key_usage_aggregates_project_credentials` was
**updated, not removed** — it now asserts `None ∈ project_ids`, that the calling key's own
`token_prefix` appears, and that the union is still sorted.

Edge case worth recording: an org that owns **zero** projects still sees its own keys — the empty-scope
short-circuit zeroes *metrics* only, so a brand-new org key is never invisible to itself.

## 5. Token prefix — decided (plan §5)

**Keep `vk_` for both.** Recorded in `phase.md` (`P10.S3 landed`) with the full reasoning and the
counter-argument, and the `Open Questions` entry is struck through and marked RESOLVED. Short form: the
prefix is never validated (auth is `sha256_hex` only), so a second prefix buys no pre-DB branch; `vk_`
is published as *the* key shape; and the honest counter-argument — a distinct prefix has real
incident-response value for humans and secret scanners — is preserved along with the note that it stays
available as a mint-side-only, purely additive change.

## 6. Cleanup — `FeedbackQueryFilters.project_id` deleted (plan §6)

Re-verified first, as instructed: `grep -rn "filters.project_id\b\|project_id=" src/vocky/feedback/
src/vocky/*.py` plus a repo-wide sweep of **every** `FeedbackQueryFilters(...)` construction in `src/`
and `tests/`. Result: **no setter anywhere**. The only readers were the `_apply_query_filters` branch
itself. Note that **S2's note was stale on one detail** — it said `tests/test_persistence.py` still
constructs the field; that file only mentions the `ix_feedback_events_project_id` **index name**, and
no test constructs it. So the cleanup was genuinely trivial: the field and its filter branch are gone,
the type's docstring now says why, and **no test needed changing**. Footgun 1's mechanism no longer
exists in the type: project scoping is expressible only as a set.

## Verification — commands and actual outcomes

| command | outcome |
|---|---|
| `make test` | **pass — 201 passed in 8.97s** (196 → 201; five new cases), green on the first run |
| `docker compose up --build -d app worker` | **pass** — rebuilt so the smoke ran against *this* slice's code, not S2's |
| `make smoke` | **pass** — `healthz ok at http://127.0.0.1:8000`; `POST /api/feedback accepted: 5b9d7cea-…`; `GET /api/feedback ok: 1 record(s)`. The per-project mint path `src/vocky/smoke.py` hard-codes is untouched. |
| `python3 scripts/workflow.py validate` | **pass** — `Workflow validation passed.` |
| live end-to-end against the running stack (extra) | **pass** — see below |

The live check, because a mint surface deserves one real round trip:
signup → `POST /app/credentials` → `{"project_id": null, "token_prefix": "vk_jn823qZyU"}` → capture with
`"project": "mobile"` → 202 → the worker persisted it → `GET /api/project/feedback` returned the record
carrying `project_id` of the get-or-created `mobile` project → `GET /api/project/usage` listed the org
key **itself** (`project_id: null`, `last_used_at` stamped) → `DELETE /app/credentials/<bogus-uuid>` →
404 → `DELETE /app/credentials/<real>` → 204 → the same key on `/api/*` → **401**.

No linter is configured in `pyproject.toml` (and `ruff` is not a project dependency, as S2 also found);
`make test` is the repo's gate.

## Inspection required by the plan

**Every new handler scopes through `ctx.tenant.id` or `get_request_project_ids`:**
`create_org_credential` writes `tenant_id=ctx.tenant.id`; `list_org_credentials` reads
`list_org_credentials(ctx.tenant.id)`; `delete_org_credential` checks
`record.tenant_id != ctx.tenant.id` (plus `project_id is not None`).

**No new code path reads `credential.project_id` as a filter.** `grep -rn "credential\.project_id"
src/vocky/` returns four sites: the two pre-existing resolvers (`auth.py:135-136`,
`capture.py:350-351`), the pre-existing serializer fork (`project_feedback_api.py:105`), and **one new
site**, `usage_api.py:257` — an org-vs-bound *shape* test that decides whether to union the org
credential rows. It selects nothing and filters nothing; the project filter on that handler is still
the `get_request_project_ids(request)` tuple. `app_api.py:379`'s `record.project_id is not None` is the
delete route's ownership check on a **session-authed** route (there is no ingest credential in play).

## Tests

One new module, `tests/test_org_credentials_api.py` (5 cases, full `create_app()` stack), plus the one
pin update described above. Terse per `AGENTS.md`; each case is a boundary the plan named:

1. **Mint → capture → read, across projects** — mint via the real route (asserting `project_id is
   None`, `token_prefix == key[:12]`, no `token_hash`), list it, capture into `alpha` and `beta` with
   the `project` field (both get-or-created; queued payloads carry the right ids), then read both back
   through `/api/project/feedback` with the one key — and confirm that key appears in its own
   `/api/project/usage`.
2. **The anti-probe rule** — a *project-bound* id of the caller's own tenant, another tenant's org id,
   and a random uuid all 404 with the identical body; a malformed uuid 400s; and nothing was revoked.
3. **Revocation** — `DELETE` → 204, the same key on `/api/*` → 401 `{"detail": "Unauthorized"}`, and
   the row stays listed with `revoked_at` set.
4. **Isolation on every per-record verb** — GET / PATCH / DELETE / POST comment / GET comments /
   attachment download against another tenant's feedback id: `[404] * 6`, one body, never 403; and the
   list surface returns `[]`.
5. **Project-bound keys are unchanged** — the per-project mint still returns `project_id == project_id`
   and the **exact** key set of the credential payload (so a future field addition is a visible edit),
   and that key does **not** appear in the org listing.

## Deviations from `plan.md`

**Two, both narrow.**

1. **`tests/test_org_credential_scope.py::_mint_credential` was *not* re-pointed at the real mint
   route.** S2 suggested it; the plan did not require it. That module mounts **route subsets**
   (`api_routes`, `project_feedback_routes`, `usage_routes`) with no `/app/*` session surface, so
   re-pointing would mean building the full app and doing a login round trip in every case, to prove
   something the new module now proves end-to-end. Its docstring was updated to say why it stays at the
   service layer and where the route-level coverage lives. Net: the mint route *is* exercised, and the
   enforcement tests stay cheap.
2. **The plan's cleanup step expected a test edit** ("update the constructing test"). None was needed —
   see §6: no test constructs the field. Recorded rather than silently skipped.

Everything else followed the plan: additive routes beside the per-project ones, the by-id read instead
of list-and-scan, the tightened 404 rule with the mirrored wording, the union with its re-sort, the pin
updated rather than deleted, the resolver left alone, and no web/CLI/doc-version work.

## Doc impact (appended to `phase.md`, not versioned here)

No `doc-new-version` was run — `P10.REVIEW` consolidates. Five one-line notes appended, and the
`security.md` one says the honest thing: **this is the slice where the published guarantee actually
changes**, because it is the first slice after which an org-scoped key can exist. `:58`'s
`NOT NULL`-anchored sentence must be rewritten to anchor on tenancy isolation + an explicit,
user-chosen key scope. The others cover `api.md` (three new routes and their exact payloads,
`project_id: null` as the org discriminator, the usage change), `backend.md` (the two new primitives,
the `org_tenant_id` parameter, the deleted filter field), `product.md` (org keys live, both kinds share
the `vk_` prefix), and `experience.md` (project key vs org key as a stated trade-off).

## Definition of done — checked

- An org key can be minted, used across every project in its org, listed, and revoked — yes, by test
  **and** live against the running stack.
- A project-bound credential id cannot be reached through any org route — yes, pinned; and the org
  listing/delete are disjoint from the per-project ones in both directions.
- Project-bound behavior is unchanged and pinned by test — yes (case 5, plus the whole pre-existing
  suite still green with one deliberate exception).
- `/api/project/usage` includes org-level keys — yes; the drill-down is unchanged.
- The prefix question is decided and recorded, counter-argument included — yes.
- Full suite + smoke pass — yes, 201 passed; smoke green against a rebuilt image.
- `result.md` + `phase.md` notes (including what S4/S5 inherit) written — this file, a
  `P10.S3 landed` section, five Doc impact lines, and the Open Questions entry resolved.
