# P10.REVIEW — phase review and doc consolidation

kind `review` · risk **high** → `slice-executor-high`

All paths relative to `/Users/sugang/projects/personal/vocky`.

## Context

P10 restructured vocky's accounts plane into user → org → project. All five middle slices are done and
committed:

| slice | what landed |
|---|---|
| `S1` | migration `20260728_1200` (de-dupe + `UNIQUE(tenant_id,name)` + `project_credentials.tenant_id` + nullable `project_id`), `provision_signup`, `get_or_create_project`, the `POST /app/projects` get-or-create fold |
| `S2` | every credential-derived project filter made set-based and org-aware behind a middleware-resolved scope; landed **dark**; a pre-existing `usage_api` fail-open defused |
| `S3` | `/app/credentials` mint/list/revoke — **org keys turned on**; usage union; `FeedbackQueryFilters.project_id` retired |
| `S4` | dashboard org-keys panel, `VockyCredential.project_id: string \| null`, Workspace → Org copy |
| `S5` | CLI `keys mint/list/revoke` with optional `--project`, Workspace → Org wording, signup default-project line |

**This slice validates all five together, judges the phase, and — only on a passing verdict —
consolidates the durable-doc versions.** Read `phase.md` end to end first: the Constraints, the four
operator decisions, the nine footguns, each slice's landed notes, and the running **Doc impact** list.

## Part 1 — Validate everything, together

Run all of it and report actual output. Do not trust the per-slice results; the point of this slice is
that the phase is green *at once*, on the current tree.

```bash
# Python: schema + suite
uv run alembic upgrade head
uv run alembic downgrade -1 && uv run alembic upgrade head   # round-trip
make test                                                    # expect ~206 passed

# The deploy smoke — rebuild first; a cached image will run stale code
docker compose up --build -d app worker
make smoke

# Web (from web/)
cd web && pnpm install && pnpm typecheck && pnpm lint && pnpm test && pnpm build

# Lean-CLI invariant: a bare venv with only httpx + typer, no server extra
#   python -c "import vocky.cli.app"      -> must import cleanly
# (S5 did exactly this; reproduce it.)

python3 scripts/workflow.py validate
```

Note: `pnpm format:check` exits 1 on **pre-existing** debt in ~12 files S4 never touched. Confirm that
is still the case and is unrelated to P10 rather than treating it as a phase failure — or, if it is
cheap and clearly pre-existing, record it as a finding for a future slice rather than fixing it here.

## Part 2 — Judge the phase

Review against the objective in `phase.json`, the confirmed intent in `intent.md`, and the docs. The
things that actually matter here:

**1. The security posture is honestly stated.** This is the phase's centre of gravity. In knowledge's
P18 the equivalent change was a *wording* update; **in vocky it is a real trust-boundary widening.**
`docs/current/security.md:58` currently anchors its guarantee on the column that this phase made
nullable — *"Because `project_credentials.project_id` is `NOT NULL`, the forced filter can never degrade
to an unscoped read."* **That sentence must be rewritten, not reworded**, to anchor on tenancy isolation
plus an explicitly user-chosen key scope. Verify the new text is true of the code, not aspirational.

**2. The objective's own wording is wrong and the docs must not inherit it.** `phase.json`'s objective
says signup provisions "a `default` org and a `default` project". **Per operator decision 3 only the
project half is true** — the org keeps `"<localpart>'s workspace"`. S1 pinned this with a test that also
asserts `vocky.accounts.service` has **no** `DEFAULT_ORG_NAME`. **The docs follow the code, not the
objective sentence.** Call this out explicitly in the review note.

**3. No fail-open survives.** Confirm by grep, not by memory, that nothing derives a project filter from
`credential.project_id`, and that every scope path ends in a non-empty set or an explicit early return.
S2's own check was `grep -rn "credential.project_id\|get_request_credential" src/vocky/`.

**4. 404-never-403 holds, including the narrower org rule.** `DELETE /app/credentials/{id}` must 404 for
a project-bound credential *of the caller's own tenant*, not merely for another tenant's.

**5. Project-bound keys are unchanged.** S2's byte-for-byte pass (191/191, zero assertion edits) is the
additivity proof — cite it; it cannot be re-derived now that minting is on.

**6. Scope discipline.** P11 owns `vocky init`, the env-var quickstart, and all landing-page marketing
copy; P12 owns deployment. Confirm no slice leaked into those.

## Part 3 — Consolidate the docs (**only on a passing verdict**)

If the verdict is `pass`, consolidate `phase.md`'s Doc impact list into new versions with
`python3 scripts/workflow.py doc-new-version --doc <name> --summary "..." --source P10.REVIEW`.
Write **only docs, never source**. Never hand-edit `docs/current/*.md` — they are generated; create
versions and let the engine regenerate.

The seeded list names **`security`, `api`, `architecture`, `backend`, `product`, `experience`, `data`**.

**Two the running list under-covers — judge whether they need versions too:**

- **`frontend`** — S4 changed the web surface materially (the dashboard org-keys panel, the nullable
  `VockyCredential.project_id`, the shared show-once component, Workspace → Org copy). No slice named
  `frontend.md` in its Doc impact notes, which looks like an omission rather than a decision.
- **`decisions`** — this phase made several durable, precedent-setting calls: no design round for the
  org-key surface, the org keeps its friendly auto-name, `vk_` stays the single key prefix (with a
  recorded counter-argument), and omitting `--project` mints an org key. `docs/current/decisions.md`
  uses a `D-P<n>-<n>` convention.

**`docs/cli.md` and `README.md` are NOT versioned docs** — they are plain files. S5 flagged specific
stale sites rather than editing them: `docs/cli.md`'s Keys section (`:91-97`), the walkthrough
(`:136-171`), wording at `:78`/`:81`/`:201`, and `README.md:78,325`, which hardcode `--project` in
`keys mint` examples. Update these directly as ordinary doc edits — they are documentation, not source.

After consolidating: `python3 scripts/workflow.py rebuild-docs` (or `docs`) and
`python3 scripts/workflow.py validate`.

## Part 4 — Return

Return a `review_verdict` of `pass | changes_requested | blocked`.

**On a non-passing verdict, STOP before any consolidation** — but complete the validation and the
judgment first, so the whole picture arrives in one cycle rather than one finding per cycle. Hand back
**numbered findings** and **proposed fix slices** (`P10.F1`, …) and let the orchestrator decide.

Do **not** write a phase explainer. Report the fixed pointer:
`explain: not written — run /explain for this phase`.

Write `works/phases/active/P10/slices/P10.REVIEW/result.md` free-form, from scratch, including the full
validation matrix with actual output.

## Definition of done

Every validation command run and reported on the current tree; the phase judged against objective,
intent, and docs; on a pass, doc versions consolidated (including a reasoned call on `frontend` and
`decisions`) and the two unversioned doc files updated; `result.md` written; the verdict returned with
the `explain` pointer.
