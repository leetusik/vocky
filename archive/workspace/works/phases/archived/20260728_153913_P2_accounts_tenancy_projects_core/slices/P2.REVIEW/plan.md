# Plan — P2.REVIEW: validate the phase & consolidate durable docs

**Slice job:** Do P2's consolidated behavioral validation and phase review, and — **only on a pass** —
consolidate the phase's `phase.md` "Doc impact" notes into new durable-doc versions. Write **only
docs, never source**. Return a `review_verdict`. Read `works/phases/active/P2/phase.md` (objective +
S1–S4 notes + the full "Doc impact" list) and `works/phases/active/P2/intent.md` first.

Objective to judge: *replace static bearer-token auth with real accounts (signup/login) + a
multi-tenant SaaS core (tenants, projects, per-project credentials); free, no billing.*

## Part A — Validate all slices together (before any doc work)

- `uv run pytest` — full suite green (expect **153**). Hard gate.
- `uv run alembic upgrade head` applies cleanly (head `20260715_1200`); `python3 scripts/workflow.py
  validate` passes.
- Scrub check: `grep -rn "api_auth_token\|APIBearerAuthMiddleware" src/ tests/` → none;
  `VOCKY_API_AUTH_TOKEN` only in `admin_assets/*` + one `test_admin_ui.py` assertion (P4-deferred).
- Confirm end-to-end from code that the objective is met: accounts (S2), tenants+projects (S1 schema,
  S3 `/app/*` CRUD), per-project credentials (S1 schema, S4 mint/list/revoke), **mandatory** `/api/*`
  credential ingest auth + static token retired (S4), free (no billing). Flag any regression, security
  gap, or scope drift.

If validation fails or the objective isn't met → **do NOT version docs**; return
`review_verdict: changes_requested` with concrete proposed fix slices (or `blocked`). Green + met →
Part B, return `pass`.

## Part B — Consolidate durable docs (ONLY on a pass)

For each doc: `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "<slug>" --source
P2.REVIEW`, write the new version content into the created `docs/versions/<doc>/vNNNN_<slug>.md`, then
`python3 scripts/workflow.py rebuild-docs`. **Never** hand-edit `docs/current/*`. Mirror the
P1.REVIEW pattern. Read each current doc first; base content on `phase.md` Doc-impact + the actual
shipped code. Version these **8** docs:

1. **product** (evolve) — drop the multi-tenant / "SaaS account, organization, billing" **non-goals**;
   Vocky is now a free multi-tenant SaaS (accounts, tenants, projects, per-project credentials; no billing).
2. **architecture** (evolve) — identity+tenancy layer; `/auth/*`, `/app/*`, credential-guarded `/api/*`;
   `src/vocky/accounts/` domain; `ProjectCredentialAuthMiddleware`; P2/P3 boundary (no feedback `project_id` yet).
3. **api** (evolve) — `/auth/{signup,login,logout,me}`, `/app/{tenant,projects,projects/{id},
   projects/{id}/credentials}`, new `/api/*` credential-auth model (mint-once `vk_`; missing/bad/revoked→401);
   status codes + cross-tenant-404 rule.
4. **data** (author stub) — six tables + columns/constraints/FKs + migration `20260715_1200`.
5. **backend** (author stub) — `accounts` domain, `require_user`/`AuthContext`/`AuthError`, `security.py`
   primitives, `auth_api`/`app_api` route modules + wiring.
6. **security** (author stub) — argon2id passwords; opaque session tokens (sha256, 30-day TTL); `vk_`
   credentials (sha256, mint-once, soft-revoke); mandatory ingest auth; no enumeration; no hash/token in responses.
7. **decisions** (author stub) — email+password + opaque DB tokens (not JWT/OAuth); multi-tenant schema,
   solo-owner MVP flow; `/app/*` control-plane vs `/api/*` data-plane; strictly-mandatory ingest auth;
   P2/P3 capture-scoping boundary.
8. **experience** (evolve) — integrate via signup → create project → mint `vk_` credential → send as
   `Authorization: Bearer` on `/api/*`; replace the old optional-static-token guidance.

Leave `frontend`, `operations`, `qa` untouched.

## Boundary & verdict

Write only `docs/` (via `doc-new-version`/`rebuild-docs`), `phase.md`, and `result.md`. Do **not**
touch source, do **not** commit, do **not** run `review-phase`/`finish-slice`/`set-*-status`. Write
`result.md` (validation results, objective assessment, docs versioned or why not) and append any
final notes to `phase.md`. Return `review_verdict: pass | changes_requested | blocked` with clear
reasoning (and proposed fix slices if `changes_requested`).
