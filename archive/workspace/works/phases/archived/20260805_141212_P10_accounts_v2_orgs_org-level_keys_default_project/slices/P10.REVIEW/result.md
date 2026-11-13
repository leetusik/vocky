# P10.REVIEW — result

**Verdict: `pass`.** All five middle slices validated together on the current tree (`726191a` + this slice's doc-only changes), the phase judged against `phase.json`'s objective, `intent.md`, and the docs, and nine durable-doc versions consolidated. `explain: not written — run /explain for this phase`.

---

## Part 1 — Validation matrix (re-run from scratch; per-slice results not trusted)

Every command below was run by this slice against the current tree. Nothing was carried over from a slice's `result.md`.

| # | command | outcome | actual output (trimmed) |
|---|---|---|---|
| 1 | `uv run alembic upgrade head` | **pass** | ends at `20260728_1200 (head)` |
| 2 | `uv run alembic downgrade -1` | **pass** | `Running downgrade 20260728_1200 -> 20260716_1600, org-level credentials: unique project names + tenant-scoped credentials`; `alembic current` → `20260716_1600` |
| 3 | `uv run alembic upgrade head` (round-trip back) | **pass** | `Running upgrade 20260716_1600 -> 20260728_1200`; `alembic current` → `20260728_1200 (head)` |
| 4 | `make test` | **pass** | `206 passed in 9.05s` (28 files; incl. `test_org_credential_scope.py` 5, `test_org_credentials_api.py` 5, `test_accounts_provisioning.py` 4) |
| 5 | `docker compose up --build -d app worker` | **pass** | exit 0 — both images **rebuilt** (`app Built`, `worker Built`) then recreated, so the smoke below ran fresh code, not a cached image |
| 6 | `make smoke` | **pass** | exit 0 — `healthz ok` → `POST /api/feedback accepted: 41781af3-…` → `GET /api/feedback ok: 1 record(s)` |
| 7 | `pnpm install` (in `web/`) | **pass** | `Done in 248ms` |
| 8 | `pnpm typecheck` | **pass** | `tsc --noEmit`, no output |
| 9 | `pnpm lint` | **pass** | `eslint .`, no output |
| 10 | `pnpm test` | **pass** | `Test Files 5 passed (5)` / `Tests 61 passed (61)` |
| 11 | `pnpm build` | **pass** | 13/13 static pages, full route table rendered |
| 12 | `pnpm format:check` | **exits 1 — pre-existing, NOT a phase failure** | 12 files, **verified disjoint from P10** (below) |
| 13 | lean-CLI invariant (bare venv) | **pass** | `vocky.cli.app imported OK` |
| 14 | `python3 scripts/workflow.py validate` | **pass** | `Workflow validation passed.` (re-run after doc consolidation — still passes) |
| 15 | live end-to-end against the running stack | **pass** | **25 checks, 25 passed, 0 failed** (below) |

### 12 — `pnpm format:check`, confirmed pre-existing and unrelated

It exits 1 on exactly 12 files:

```
README.md · src/app/(app)/projects/[projectId]/actions.ts · src/app/apple-icon.tsx
src/app/opengraph-image.tsx · src/lib/bff.ts · src/lib/env.ts · src/lib/session.ts
src/lib/vocky/auth.ts · tests/auth-routes.test.ts · tests/session-guards.test.ts
tests/session.test.ts · tests/vocky-auth.test.ts
```

Rather than take S4's word for it, I intersected that list with the actual file set P10 changed
(`git diff --name-only 0f68c1e~1 726191a`, 68 files). **The intersection is empty** — P10 touched none
of these 12. This is P4-era debt, not a P10 regression, and it is recorded as a **finding for a future
slice** (see below), not fixed here: reformatting files outside a phase's blast radius inside its review
is exactly the kind of drive-by the small-diff rule exists to prevent.

### 13 — lean-CLI invariant, verified live rather than by grep

Built a throwaway venv and installed **only** the base dependency group — the literal
`pip install vocky` scenario, no `server` extra:

```
Package           Version      (13 packages, no fastapi/sqlalchemy/pydantic/starlette/redis)
httpx 0.28.1 · typer 0.27.0 · rich · click-adjacent deps · vocky 0.1.0
```

```
$ leancli/bin/python -c "import vocky.cli.app; print('vocky.cli.app imported OK')"
vocky.cli.app imported OK

$ leancli/bin/vocky keys --help
  mint    Mint a `vk_` ingest key for a project, or for the whole org (shown once).
  list    List a project's credentials, or the org's (metadata only; never the key).
  revoke  Revoke (soft-delete) one of a project's keys, or an org-level key.
```

The invariant holds: `src/vocky/cli/*` pulls in nothing outside `typer` / `httpx` / `vocky.cli.*`, and
`client.py:27 → vocky.smoke.make_http_user_agent → httpx` remains the only hop into a non-CLI module.

### 15 — live end-to-end verification (this slice's own, not S3's)

S3 did a live pass; the review did its own against the freshly rebuilt stack, because the point of this
slice is that the phase is green *at once*. 25 assertions, all passing:

```
PASS  signup 201
PASS  org keeps friendly auto-name (decision 3)              -- rev0492049315's workspace
PASS  signup provisions a "default" PROJECT (not a "default" org)
PASS  POST /app/projects idempotent on name, 201 both times, same id
PASS  POST /app/credentials 201
PASS  org credential serializes project_id as JSON null (not "None")
PASS  org key carries the vk_ prefix (decision: one prefix)
PASS  per-project mint still 201
PASS  project-bound credential payload key set unchanged
        ['created_at','id','last_used_at','name','project_id','revoked_at','token_prefix']
PASS  DELETE /app/credentials 404s for the caller's OWN project-bound key  -- 404 {"detail":"credential not found"}
PASS  ...identically to a nonexistent id (indistinguishable)
PASS  malformed uuid -> 400
PASS  org key capture with project=mobile accepted           -- 202
PASS  org key capture without project accepted               -- 202
PASS  project-bound key accepts and ignores the project field -- 202
PASS  project-bound key created NO project from the ignored name -- ['default','mobile']
PASS  org key's unnamed capture landed in "default"
PASS  org key reads >1 project's feedback                    -- 3 records
PASS  org-key records CARRY project_id
PASS  project-bound records OMIT project_id (unchanged contract) -- 2 records
PASS  org key's own usage view lists the org key itself      -- [None, 'fe0f9690-…']
PASS  per-project drill-down does NOT list org keys (unchanged)
PASS  org key NEVER reads another tenant's feedback          -- 3 records, none foreign
PASS  revoke org key -> 204
PASS  revoked org key -> 401 on /api/*

RESULT: 25 passed, 0 failed
```

Two notes on the run itself: the first two attempts failed on **my own** payload shape
(`source_product`/`comment` instead of `message` + `source.product`, and `feedback_value: 0` — valid
values are 1/2). Both were harness bugs in the review script, corrected and re-run; neither indicated
anything about the code. Recording that here so a later reader does not mistake the intermediate
output for a real failure.

---

## Part 2 — Judgment

### 1. The security posture is honestly stated (the phase's centre of gravity)

**The retired sentence is gone.** `security.md`'s old guarantee — *"Because `project_credentials.project_id`
is `NOT NULL`, the forced filter can never degrade to an unscoped read"* — no longer appears as an
assertion anywhere. It survives in exactly one place: quoted inside a new lead section that names it and
**explicitly retires it**. That is deliberate; silently deleting a published guarantee is worse than
retiring it in the open.

It was **rewritten, not reworded**. The new `## Ingest Key Scope — the P10 trust-boundary change (read
this first)` section opens the doc's body and states the change as a real widening, anchored on two
things I verified in code rather than on the reference implementation's framing:

- **(a) tenancy isolation**, unconditional — `tenant_id` is `NOT NULL` on *every* credential row at both
  scopes, and the caller-supplied capture `project` is a **name** get-or-created strictly under the
  credential's own `tenant_id` (`capture.py:353-362`), so it can never reach or create a project in
  another org;
- **(b) an explicitly user-chosen key scope**, project-bound or org-level, reported to clients as
  `project_id` (UUID vs `null`).

And the mechanism section states why the new argument is *stronger* than the old one: it does not
depend on the column at all. Everything asserted there was checked against source, not against
`phase.md`:

| claim in the new doc | verified against |
|---|---|
| scope resolved once in middleware, `tuple`, never `None` | `auth.py:112-141`, `:197-215` |
| an unscoped project read is not expressible in the type | `FeedbackQueryFilters` has no `project_id` (`feedback/types.py:120-135`) |
| empty scope short-circuits, never collapses to `None` | `api.py:255-258`, `project_feedback_api.py:128-133`, `usage_api.py:148,206-213`, `app_feedback_api.py:143-146` |
| scope resolution fails **closed** with a 500 | `auth.py:202-214` (contrast the swallowed `last_used_at` stamp at `:216-227`) |
| enqueue is the last write-path enforcement point | `capture.py` `resolve_capture_project` never returns `None` |

**Blast radius is stated plainly**, not softened: an org key exposes every project in the org, present
and future, for capture, read, **and** manage (including delete); revoking it cuts every project at
once. The `vk_`-prefix decision carries its **counter-argument recorded honestly** (a distinct prefix
would help a human, a log scrubber, or a secret scanner tell a broad key from a narrow one at a glance),
and notes that nothing forecloses adding one later.

Nothing in the new text is aspirational. Two things I deliberately did **not** claim:

- I did **not** say signup is atomic. `create_user` still commits ahead of `provision_signup`, so the
  org-less-user window is **narrowed, not closed** — said in exactly those words in `security.md`,
  `architecture.md`, and `backend.md`.
- I did **not** claim per-credential permission scopes. An org key has the *same* full verb set as a
  project key; only its reach widened. `security.md` says so, because "broad scope **and** full verbs" is
  precisely why the org key is the bigger secret.

### 2. The phase objective is partly wrong, and the docs follow the code

`phase.json`'s objective says signup provisions "a `default` org **and** a `default` project". **Only
the project half is true.** Per operator decision 3 the org keeps `"<localpart>'s workspace"`, and S1
pinned it with a test asserting the friendly name **and** the absence of any `DEFAULT_ORG_NAME`
attribute on `vocky.accounts.service`.

Re-verified live, not read from a note: signup for `rev0492049315@example.com` returned
`tenant.name == "rev0492049315's workspace"` and `project.name == "default"`.

**The docs follow the code**, and say so explicitly rather than quietly diverging. The divergence is
called out by name in four places:

- `api.md` — under `POST /auth/signup`: *"Only the project is named `"default"`; the org keeps its
  friendly auto-name"*, with the reasoning and the pinning test.
- `product.md` — *"Note this contradicts an earlier phrasing of the P10 objective … only the project
  half is true, and the docs follow the code."*
- `decisions.md` — **D-P10-2**, which records it as a deliberate divergence from *both* the reference
  implementation and the phase objective's own wording.
- `data.md` and `experience.md` carry the same distinction where a reader would otherwise infer "default
  org".

**Recommendation to the orchestrator:** `phase.json`'s `objective` string is still the stale wording. It
is phase metadata, not a doc, and a review slice does not transition or rewrite phase state — so I left
it. Worth correcting when the phase is recorded, or accepting as a historical record now that every
durable doc contradicts it explicitly.

### 3. No fail-open survives — verified by grep, then by reading every hit

Ran S2's own check on the current tree:

```
$ grep -rn "credential.project_id\|get_request_credential" src/vocky/
```

**Zero filter sites derive a project scope from `credential.project_id`.** Every remaining read is one of
three deliberate non-filter uses, each confirmed by reading the code:

| site | what it does | why it is not a filter |
|---|---|---|
| `auth.py:135-136` | the scope resolver itself | this is where the tuple is *produced* |
| `capture.py:350-351` | the capture resolver | picks a destination, returns a `UUID`, never `None` |
| `usage_api.py:242-257` | shape test for the org-key union | commented in-code as *"read here as a shape test, never as a filter"*; the filter is `scope` |
| `project_feedback_api.py:105` | serializer fork (adds `project_id` for org callers) | changes output shape, not the query |

I also confirmed **every scope path terminates safely** — either an explicit early return or set
membership that fails closed on an empty set:

- `api.py:255-258` — `if not scope: return {"records": []}`
- `project_feedback_api.py:128-133` — same, and `:85` `record.project_id not in project_ids` (always true
  for an empty tuple → 404)
- `usage_api.py:148` and `:206-213` — `if not project_ids:` → zeroed metrics, with an in-code comment
  saying *"Deliberately **not** `project_ids or None`"*
- `app_feedback_api.py:143-146` — the original pattern the rewrite copied
- `feedback/repository.py:562` — `if filters.project_ids is not None:` (the safe form; a truthiness test
  would have been the fail-open)

And structurally: `FeedbackQueryFilters.project_id` **is deleted** — I grepped the type, not the note.
An unscoped project read is no longer expressible.

### 4. 404-never-403 holds, including the narrower org rule

Read in code (`app_api.py:354-383`) and **exercised live**. `DELETE /app/credentials/{id}` 404s unless
the row is *both* `tenant_id == ctx.tenant.id` **and** `project_id IS NULL`. The live run confirmed the
sharp part: a **project-bound credential of the caller's own tenant** answered
`404 {"detail":"credential not found"}` — and byte-identically to a random nonexistent UUID (same status,
same body), so the two are genuinely indistinguishable. A malformed UUID answers `400`, which is a shape
error and leaks no existence. Pinned by
`tests/test_org_credentials_api.py::test_org_delete_is_404_never_403_even_for_a_bound_key`
(`[404, 404, 404]`).

### 5. Project-bound keys are unchanged — citing S2's proof, as instructed

S2's dark landing passed the entire pre-existing suite **191/191 byte-for-byte with zero assertion
edits**. That proof is structural and **cannot be re-derived now that minting is on**, so it is cited
rather than re-run — and it is recorded in `security.md` and `decisions.md` (D-P10-3) as *the*
additivity evidence, with the reason it is unrepeatable.

What I *could* still check on the current tree, I did: the live run confirmed the project-bound
credential payload's key set is unchanged, a project-bound `/api/project/feedback` response still omits
`project_id`, the per-project usage drill-down still lists no org keys, and a project-bound key sent a
bogus `project` name and **created no project** from it (`['default','mobile']` only).

### 6. Scope discipline — no leakage into P11 or P12

Verified mechanically against the phase's commit range:

- **`vocky init`** — `grep` over `src/vocky/cli/`: no such command exists. P11's.
- **Landing copy** — `web/src/content/landing.ts` appears **0 times** in P10's diff. P11's.
- **Deployment** — 0 files matching `docker|compose|deploy|.github|Dockerfile|Caddy|nginx` in P10's diff. P12's.
- **Workspace → Org** — `grep -rn -i workspace src/vocky/cli/ web/src/` returns **nothing**, so the
  rename is complete in both client surfaces and did not stop halfway.

---

## Part 3 — Doc consolidation (pass-only; nine versions)

All created with `doc-new-version --source P10.REVIEW`, edited at the returned `edit_path`, then
`rebuild-docs`. **No `docs/current/*.md` was hand-edited** and **no source file was touched** — confirmed
by `git status`: the only non-doc changes are `docs/index.json` and `works/events.jsonl`, both engine-written.

| doc | version |
|---|---|
| `security` | `v0008` — the trust-boundary rewrite (the phase's centre of gravity) |
| `api` | `v0008` — additive signup `project`, get-or-create projects, three org routes, nullable `project_id`, the capture `project` name |
| `architecture` | `v0009` — user→org→project, the request-scoped credential-scope chokepoint, enqueue-is-last-enforcement |
| `backend` | `v0005` — the new accounts/auth/capture primitives, with the load-bearing `except`-nesting warning |
| `data` | `v0004` — migration `20260728_1200`'s four load-bearing phases + the destructive downgrade |
| `product` | `v0009` — user→org→project, signup lands usable, a key is a scope choice |
| `experience` | `v0010` — onboarding is two steps not three; "names are not unique" corrected |
| `frontend` | `v0006` — **the reasoned addition** (see below) |
| `decisions` | `v0007` — **the reasoned addition**: D-P10-1..5 |

### The two judgment calls the plan asked for

**`frontend` — versioned. The omission was an oversight, not a decision.** S4 changed the web surface
materially and `frontend.md` is the doc that describes exactly that layer. Left unversioned it would
have kept asserting four things that are now false: `VockyCredential.project_id: string` (it is
`string | null`, and `null` is the org-key discriminator), *"Exactly **3** [server actions] are
registered app-wide"* (it is **5** — I counted the `export async function`s), *"56 vitest tests"* (61),
and *"13 P4-era"* format-check files (12). It also lacked any record of the org-keys panel, the shared
`ShowOnceKey` component, or the Workspace→Org rename. Three new frontend constraints were added, since
they are the ones a future contributor would otherwise break: narrow the nullable `project_id` (never
cast, never fork the type), keep `ShowOnceKey` shared, and keep the two key surfaces disjoint.

**`decisions` — versioned. The phase made durable, precedent-setting calls.** `decisions.md` exists to
stop settled questions being re-litigated, and P10 settled five. Added under the existing `D-P<n>-<n>`
convention:

- **D-P10-1** — "Org" is product-facing naming only; no `tenants` → `orgs` rename.
- **D-P10-2** — signup provisions a `"default"` **project**; the org keeps its friendly name. Records the
  divergence from the reference implementation *and* from the objective's wording.
- **D-P10-3** — org keys are a real trust-boundary widening, landed **additively and enforcement-first**.
  Marked as **narrowing D-P3-2** (a key's "both, full" authority now spans a *chosen* scope), and the
  Status section says so. This is the one that most needed writing down: the *ordering* (enforcement
  dark, before the mint surface) is the safety property, not a preference.
- **D-P10-4** — one `vk_` prefix for both scopes, **with the counter-argument recorded**.
- **D-P10-5** — omitting `--project` mints an org key (and the accepted exit-2 cost); no design round for
  the org-key surface, which ships as a dashboard panel.

### The two unversioned plain files, updated directly

**`docs/cli.md`** — every site S5 flagged: the Keys section rewritten as a six-row table covering both
scopes (with the disjointness rule and the `Scope:` line), the walkthrough restructured (signup now
shows the additive `project` field; "create a project" demoted to an optional step 2b; mint shows both
scopes with raw-HTTP equivalents for each), a new org-key capture example, the load-bearing note that
**the plaintext key remains the strict last line** of `keys mint` output even with the added scope line,
the MCP section's "the project is implicit in the key" corrected, and the three Workspace→Org wording
sites. Added a call-out box for the relaxed-`--project` hazard.

**`README.md`** — the identity model rewritten (org + `"default"` project + the two key scopes, with a
note that `tenant` and `org` are the same thing), the quickstart spine reordered to match reality
(signup → mint → capture → read → manage, with both mint scopes and an org-key capture body), and the
two hardcoded `--project` `keys mint` examples S5 flagged. Also corrected eight "per-project `vk_`
credential" phrasings that now read as *the only kind of key*.

---

## Findings (non-blocking — recorded, not fixed here)

None of these affects the verdict. Each is recorded rather than fixed because a review slice may not
edit source, and because fixing debt outside the phase's blast radius inside its own review is the
wrong place for it.

1. **`pnpm format:check` fails on 12 pre-existing P4-era files.** Verified disjoint from everything P10
   touched. A good standalone or deferred job; do not fold it into a feature slice.
2. **`vocky keys --help`'s group docstring still reads "Mint, list, and revoke a project's `vk_` ingest
   keys."** All three sub-command docstrings correctly mention both scopes; only the group line is
   narrow. One-line CLI copy fix — natural to fold into **P11**, which owns CLI onboarding ergonomics.
   (Source, so out of this slice's reach.)
3. **`phase.json`'s objective still says signup provisions "a `default` org".** Wrong per decision 3;
   every durable doc now contradicts it explicitly. Orchestrator's call whether to correct the metadata.
4. **`README.md:34` still says the packaged Admin Web UI "still ships under `/admin` … scheduled for
   removal in P6".** P6 deleted it. Pre-existing P6-era staleness, unrelated to P10 — left alone
   deliberately rather than reaching into another phase's territory from this review.
5. **`alembic check` reports a spurious `remove_index ix_feedback_events_search_trgm`.** Pre-existing
   since `20260716_1600` (the trigram index is deliberately unmodelled). Not caused by P10, but any
   future `alembic check` CI gate must whitelist it. Now recorded in `data.md`.

---

## Deviations from `plan.md`

**One, and it is an addition rather than a departure.** The plan's Part 1 did not ask for a live
end-to-end run; I added one (row 15, 25 assertions) because several of the plan's Part 2 judgments —
the narrower 404 rule, decision 3's naming, the capture-project resolution, the usage union — are
behavioral claims that a green unit suite does not by itself demonstrate on a freshly built image. It
found no problems; it upgraded "the tests say so" to "the running system does so".

Everything else follows the plan: all listed commands run and reported with actual output, all six Part-2
judgments made, consolidation performed only after the verdict was `pass`, both under-covered docs
decided with reasons recorded, both plain files updated, no source touched, no state transitioned, no
commit made, and no explainer written.
