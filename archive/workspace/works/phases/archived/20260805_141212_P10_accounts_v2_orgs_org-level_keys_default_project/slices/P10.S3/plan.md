# P10.S3 — Org-key mint surface

kind `implementation` · risk **high** → `slice-executor-high` · depends `P10.S2`

## Context

S1 made the schema permit `project_credentials.project_id IS NULL`. S2 made **every** credential-derived
project filter set-based and org-aware, resolved once in the middleware behind
`vocky.auth.get_request_project_ids(request) -> tuple[UUID, ...]` — a type that cannot be `None`, so an
unfiltered cross-tenant read is unrepresentable. The entire pre-existing suite passed byte-for-byte,
191/191, with zero assertions edited. **Cite that proof; do not re-derive it.**

**S3 turns org keys on.** It is the slice that actually widens the trust boundary, and it is only safe
because S2 landed. Read `works/phases/active/P10/phase.md` — specifically the `P10.S2 landed` section
(the S3 handoff and the gotchas) — before writing anything.

After this slice, a `vk_` key minted at org level authorizes capture and read/manage across **every**
project in its org. Existing project-bound keys must remain **byte-for-byte identical**.

## Scope

### 1. Accounts layer — org-level credential queries

`src/vocky/accounts/repository.py` + `src/vocky/accounts/service.py`:

- **`list_org_credentials(tenant_id) -> tuple[ProjectCredentialRecord, ...]`** —
  `WHERE tenant_id = :tid AND project_id IS NULL`, ordered `created_at, id` (the house ordering).
  Includes revoked rows, like `list_project_credentials`.
- **`get_credential(credential_id) -> ProjectCredentialRecord | None`** — a plain by-id lookup.
  Today `delete_credential` (`src/vocky/app_api.py:269-295`) scopes by *listing a project's credentials
  and scanning in Python* because no by-id read exists. **Do not inherit that shape** for the org route
  — one indexed read plus an ownership check is both clearer and O(1). Leave the existing per-project
  route alone; rewriting it is not this slice's job.

### 2. The org-level routes (`src/vocky/app_api.py`)

Three routes, **additive beside** the per-project ones, session-authed via `require_user` exactly like
their neighbours:

| route | behavior |
|---|---|
| `POST /app/credentials` | mint an org key: `project_id=None`, `tenant_id=ctx.tenant.id`. Optional `{name?}` body via the existing `_parse_optional_body` + `CreateCredentialInput`. Returns `201 {credential, key}` — the same shape as the per-project mint, plaintext returned once. |
| `GET /app/credentials` | `200 {credentials: [...]}` from `list_org_credentials`, oldest-first, incl. revoked. |
| `DELETE /app/credentials/{credential_id}` | `204`. `400` on a malformed UUID. |

Key generation is unchanged: `key = f"vk_{generate_opaque_token()}"`, `token_prefix = key[:12]`,
`token_hash = sha256_hex(key)`.

**404-never-403, and it must be tighter than it looks.** `DELETE /app/credentials/{id}` answers `404`
unless the credential is *both* `tenant_id == ctx.tenant.id` **and** `project_id IS NULL`. So a
**project-bound** credential id 404s through this route just as another tenant's does — a caller can
neither revoke nor probe one through the org surface. Mirror the existing anti-probe wording in
`src/vocky/app_api.py`'s per-project delete.

### 3. The resolver — verify, don't invent

S2 already handles the org branch in `resolve_credential_project_ids` (`src/vocky/auth.py:112-136`):
project-bound ⇒ `(credential.project_id,)` with no DB call; org-level ⇒ the tenant's project set.
**S3 adds no resolver logic.** Confirm by reading it and say so in `result.md`.

Knowledge's "vanished project ⇒ unresolvable" guard (`../knowledge/server/api_auth.py:133-187`) has **no
vocky analogue to port**: vocky's resolver never loads the project, and `project_credentials.project_id`
is `ON DELETE CASCADE`, so a deleted project takes its bound credentials with it. Record that reasoning
rather than adding a guard for a state that cannot exist.

### 4. The S3 handoff S2 flagged — do not forget this

`/api/project/usage` builds its `credentials` array by looping `list_project_credentials(project_id)`
over the scope. **A per-project listing cannot return org-level rows.** Union `list_org_credentials`
into `_project_usage_response` (`src/vocky/usage_api.py`) for an org-scoped caller — otherwise **an org
key's own usage view omits the very keys it was minted as.**

There is a `NOTE for P10.S3` comment at the exact line, and `tests/test_org_credential_scope.py` pins the
current incomplete behavior **on purpose**, so your fix shows up as a visible test edit. Update that pin;
do not delete it.

Watch the ordering gotcha S2 recorded: concatenating per-project listings does not yield a globally
`created_at`-ordered list. Sort the unioned result.

### 5. Decide the open question: token prefix

`phase.md § Open Questions` leaves "distinct org-key token prefix?" open for this slice.

**Decision: keep `vk_` for both.** Record it in `phase.md` with the reasoning, including the
counter-argument, so the review sees a decision rather than an omission:

- The prefix is never validated — auth resolves purely by `sha256_hex` (`src/vocky/auth.py`), so a
  second prefix buys **no** cheap pre-DB branch, which was the only mechanical argument for it.
- `vk_` is published as *the* key shape in `docs/current/` and on the landing page. Forking it mid-phase
  fragments that story for a distinction the product surfaces explicitly anyway — S4 shows scope in the
  dashboard, S5 in CLI output.
- **The counter-argument, recorded honestly:** a distinct prefix would let a human or a secret-scanning
  rule tell a broad key from a narrow one at a glance, which has real incident-response value. If that
  is ever wanted it is a purely additive change (mint-side only), so nothing here forecloses it.

### 6. Cleanup: retire the dead single-project filter (do this only if it stays trivial)

S2 recorded that **`FeedbackQueryFilters.project_id` is now dead in `src/`** — nothing in production code
sets it; only `_apply_query_filters` still honors it and `tests/test_persistence.py` constructs it. It is
the exact field whose `None`-means-no-filter semantics is footgun 1, so deleting it removes the footgun's
mechanism rather than just its call sites.

Re-verify with `grep -rn "filters.project_id\b\|project_id=" src/vocky/feedback/ src/vocky/*.py` first.
**If any production setter still exists, leave the field alone and record why** — a live consumer means
this is not the trivial cleanup it appears to be, and S3 has more important work. If it is genuinely
dead, remove the field and its `_apply_query_filters` branch and update the constructing test.

## Not this slice

Web (`web/**`), CLI (`src/vocky/cli/**`), and all durable docs. **No `doc-new-version`** — append one-line
**Doc impact** notes to `phase.md`; `P10.REVIEW` consolidates. The security-doc rewrite in particular is
the review's job, but S3 must leave it an accurate note: **this is the slice where the published
guarantee actually changes**, because it is the first slice after which an org-scoped key can exist.

## Tests

Terse, and aimed squarely at the boundary now being opened. `tests/test_org_credential_scope.py` already
constructs org credentials at the service layer; this slice can finally mint them through the route.

- **Mint → capture → read, across projects.** One org key captures into two different named projects
  (get-or-created on first use) and reads both back through `/api/project/feedback`.
- **Isolation holds.** An org key sees nothing from a second tenant — 404, never 403 — on every
  per-record verb.
- **Revocation.** `DELETE /app/credentials/{id}` → 204, then `/api/*` with that key → 401.
- **The anti-probe rule.** A *project-bound* credential id 404s through `DELETE /app/credentials/{id}`,
  and another tenant's org credential id 404s too.
- **Project-bound keys are unchanged** — assert at least one existing-shape response explicitly, so the
  additive claim is pinned rather than assumed.
- **The usage union** — an org key's `/api/project/usage` lists its own org-level key.

## Verification

```bash
make test                            # every existing test still green + the new cases
make smoke                           # the deploy smoke: signup -> project -> mint -> capture
python3 scripts/workflow.py validate
```

`make smoke` matters here specifically: `src/vocky/smoke.py` hard-codes the per-project mint path, which
this slice must leave untouched.

Then, as in S2, verify by inspection and record it in `result.md`: confirm every new handler scopes
through `ctx.tenant.id` or `get_request_project_ids`, and that **no** new code path reads
`credential.project_id` as a filter.

## Definition of done

An org key can be minted, used across every project in its org, listed, and revoked; a project-bound
credential id cannot be reached through any org route; project-bound behavior is unchanged and pinned by
test; `/api/project/usage` includes org-level keys; the prefix question is decided and recorded; the full
suite and the smoke pass; `result.md` and the `phase.md` notes (including what S4 and S5 inherit) are
written.
