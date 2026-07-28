# Intent — P10

- Captured at: 2026-07-28T16:05:11+09:00
- Origin: operator

## Original Input (verbatim)

_One `/create-phase` run created P10, P11 and P12 from this single request; the full original is preserved in each.
**P10 owns the "org/project, key, like stuff" half** of the clarified answer._

> and revise phases. reference how ../knolwedge did. We'll follow them.

Follow-up (same session, answering the clarifying questions):

> 1. I meant learn how it implemented and we'll follow that in general. like org/project, key, like stuff. how to
> user to install etc..

> don't need to change anything. about it. while you asking this question. i /update-workspace already.

## Confirmed Intent (refined + clarified)

Learn from how the sibling repo `../knowledge` **implemented** its accounts plane (its P18, "Accounts v2:
user/org/project with org-level keys") and follow that design in vocky. Concretely, restructure vocky's accounts
plane from today's user / tenant (`"<localpart>'s workspace"`) / project shape into an explicit
**user → org → project** model:

- **No `tenants` → `orgs` table rename.** Following knowledge's design stance #1: the tenant id threads through the
  schema, the auth resolver, the `/app/*` surface, `feedback_events.project_id`'s owner chain and the web BFF; a
  rename is a large mechanical diff with prod-regression risk and **zero behavior change**. The tenant row *is* the
  org. "Org" becomes product-facing naming in web copy, CLI output, and docs only.
- **Signup auto-provisions a `"default"` org and a `"default"` project.** Today `src/vocky/auth_api.py:142` names
  the tenant `f"{payload.email.split('@')[0]}'s workspace"` and creates **no project at all** — so a fresh account
  has zero projects and zero keys, and the landing page's depicted "create a project, mint a key" step is manual
  dashboard work. Existing tenants are **not** renamed; they gain `"default"` lazily via get-or-create.
- **`projects` gains `UNIQUE(tenant_id, name)` and get-or-create-by-name.** There is no unique constraint today
  (`alembic/versions/20260715_1200_add_accounts_tenancy.py`), no `get_project_by_name`, and the only writer is the
  explicit `POST /app/projects` route (`src/vocky/app_api.py:187`) — so duplicate-named projects are silently
  allowed and an idempotent `vocky init` has nothing to build on.
- **Credentials become mintable at org level**: `project_credentials.tenant_id` NOT NULL (three-phase backfill),
  `project_id` **nullable**, and `project_id IS NULL` ⇒ org-level — a nullable column, not a scope enum, exactly as
  knowledge did it. One `vk_` key then works across every project in the org.

**Premise correction recorded during refinement — vocky differs from knowledge here, and it is the phase's central
design question.** In knowledge, org-level keys were only a *wording* change: its resolver already returned
`ctx.tenant_id` for a `vk_` key and its write path authorized by tenant, so "org-level" made de-facto behavior
honest without loosening enforcement. **Vocky is not in that position.** `ProjectCredentialAuthMiddleware`
(`src/vocky/auth.py:129-145`) resolves a credential by `token_hash` alone and never resolves a tenant on the ingest
path; every handler then scopes by `credential.project_id` — capture stamping at `src/vocky/api.py:99` and
`src/vocky/tools/capture_feedback.py:103`, the read/manage surface at `src/vocky/project_feedback_api.py:66-94`.
Vocky's keys are project-bound at **both** binding and enforcement, and `docs/current/security.md` publishes that as
a guarantee ("one `vk_` key captures/reads/manages *its* project, no per-credential scopes").

Therefore, in vocky org-level keys are a **real trust-boundary widening**, and must be **additive**:

- A newly-minted **org key** is a new, broader credential the user explicitly opts into.
- Every **existing project-bound key keeps its current behavior byte-for-byte** — same binding, same enforcement,
  same 404-never-403 isolation.
- With an org key there is no bound project, so `POST /api/feedback` must take the project from the request (by
  name, get-or-create), and `project_feedback_api.py` needs an org-scoped read/manage mode.
- This is a genuine security-doc change, **not** a doc-wording update. The phase must document it honestly.

**Out of scope, deferred**: creating additional orgs, inviting members, roles/teams. The `tenant_members` table and
its `role` column already exist (only `"owner"` is ever written, `src/vocky/accounts/service.py:117`), so the schema
supports it — but the UI/API for it is not this phase. Parked as a deferred job sourced from P10.

## Clarifications Resolved

- Q: "Revise phases" — do you mean adopt knowledge's phase-*authoring* conventions, mirror its *roadmap*, both, or
  rescope the in-flight P6? — A (verbatim): "1. I meant learn how it implemented and we'll follow that in general.
  like org/project, key, like stuff. how to user to install etc.." → **the implementation substance**, not the
  workflow conventions. P10 takes the org/project/key half.
- Q: Which new phases should I create now? — A: Accounts v2, Frictionless onboarding, Post-launch hardening.
  **Public/shareable feedback (knowledge's P19 analogue) was offered and deliberately not selected** — it is not
  planned.
- Q: Where should the adopted phase-authoring conventions be recorded? — A (verbatim): "don't need to change
  anything. about it. while you asking this question. i /update-workspace already." → **no change to `CLAUDE.md` /
  `AGENTS.md` or any workflow machinery.**

## Notes

- **Sibling phases from the same request**: P11 (frictionless onboarding — install, env-var quickstart, agent skill
  on the landing) and P12 (post-launch hardening). Execution order **P10 → P11 → P12**: P11's landing copy depicts
  the org / default-project / key flow that P10 finalizes, so the accounts model must settle first. This mirrors
  knowledge's own P18 → P20 argument.
- **P6 stays ahead of all three, but no longer deploys.** Per the operator (verbatim: _"mind that deploy will be
  done at p12 so p6 doesn't have to mind it"_), the production bring-up moved from `P6.S10` to **P12**; P6 now ends
  with every deploy artifact authored and validated statically and nothing deployed. `P6.S9` is still `pending` on
  the operator (`uv publish`), then `P6.REVIEW`.
- **That ordering is load-bearing for this phase.** Landing first means this migration runs against an **empty
  schema**, not as a live cutover on production data — which removes the migration-before-code hazard, the
  defensive de-dupe of already-existing duplicate rows, and the narrow mint/create failure window entirely. Those
  footguns are still listed below because they return the moment vocky *is* live; they simply do not apply to the
  first landing. **If the deploy order ever changes back, re-read them as blocking.**
- **Reference material in `../knowledge`, worth reading at DECOMP time** (read-only; never edit that repo):
  - `works/phases/active/P18/intent.md` and `.../P18/phase.md` — the design stances, the risk arguments, and the
    cross-slice "landed" notes
  - `alembic/versions/0003_org_level_credentials.py` — the migration shape: defensive oldest-wins de-dupe of
    duplicate `(tenant_id, name)` projects *before* the UNIQUE (`first_value(id) OVER (PARTITION BY tenant_id, name
    ORDER BY created_at, id)`, deliberately the same order `get_project_by_name` resolves), then the three-phase
    backfill for `project_credentials.tenant_id`, then `project_id` → nullable
  - `server/api_auth.py` `_resolve_tenant_bearer` — the org-vs-project resolver branch, including the "vanished
    project ⇒ unresolvable" guard preserved **only** where `project_id` is set
  - `server/accounts/service.py` — `provision_signup()` (one transaction: tenant + owner membership + default
    project) and the get-or-create primitive (read-first → insert → catch `IntegrityError` → rollback → re-read)
  - `cli/src/knowledge_cli/knowledge.py:94` `default_project()` — git-repo-root basename → stored config →
    `"default"`, with a `derived=` flag so the error message doesn't blame the user for a name they never typed
- **Known footguns recorded in knowledge's phase.md / result.md — carry these into DECOMP:**
  - **NULL-safe credential serialization.** Once `project_id` is nullable, `str(record.project_id)` serializes org
    rows as the literal string `"None"`. Knowledge caught this before it shipped only because the schema slice wrote
    no NULL rows. The fix also widens the TypeScript type to `string | null`, forcing a narrow at every web consumer.
  - **Migration-before-code ordering is load-bearing at cutover.** The new code reads a column the migration adds —
    deploying code first 500s *every* `vk_` request. Safe overlap is old-code + new-schema only, and even that has a
    narrow window where a mint or a duplicate-name create fails.
  - **Pre-check prod for duplicate `(tenant_id, name)` projects** (read-only `GROUP BY … HAVING count(*) > 1`)
    before the UNIQUE lands, so the operator knows what will be merged.
  - **Gated tests build schema via `create_all`, so they never exercise the real migration.** Knowledge's review
    added an alembic upgrade+downgrade round-trip smoke specifically to de-risk this.
  - **A behavior change breaks existing tests silently** — signup provisioning a default project will make any exact
    project-set assertion stale. That is a direct consequence, not scope creep.
- vocky's `feedback_events.project_id` is nullable with legacy NULL rows
  (`alembic/versions/20260716_1500_add_feedback_project_id.py`) — the de-dupe step must repoint it alongside
  `project_credentials`.
- Deferred from this phase: org management (create additional orgs + invite members + roles). File the deferred job
  sourced from P10 at decomposition.
