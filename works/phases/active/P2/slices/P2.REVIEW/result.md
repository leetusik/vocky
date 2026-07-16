# Result — P2.REVIEW: phase validation & durable-doc consolidation

**Verdict: `pass`.** All four implementation slices validate together, the phase objective is met
end-to-end from the shipped code, and the phase's durable-doc versions have been consolidated.

## Part A — Validation

| Check | Command | Outcome |
| --- | --- | --- |
| Full test suite (hard gate) | `uv run pytest` | **153 passed in ~6s** |
| Migrations apply cleanly | `uv run alembic upgrade head` | clean; `alembic current` = `20260715_1200 (head)` |
| Workflow state integrity | `python3 scripts/workflow.py validate` | passed |
| Scrub (old ingest auth gone) | `grep -rn "api_auth_token\|APIBearerAuthMiddleware" src/ tests/` | none found |
| Scrub (static env token) | `grep -rn "VOCKY_API_AUTH_TOKEN" src/ tests/` | only `admin_assets/docs.json`, `admin_assets/app.js`, and `tests/test_admin_ui.py:232` — all P4-deferred, as designed |

Environment: Postgres (`vocky-postgres-1`, port 55432) and Redis (`vocky-redis-1`, port 56379) were up;
the integration suite ran against the real DB.

### Objective assessment (met, verified against source)

Objective: *replace static bearer-token auth with real accounts (signup/login) + a multi-tenant SaaS
core (tenants, projects, per-project credentials); free, no billing.*

- **Accounts (S2)** — `src/vocky/auth_api.py`: `POST /auth/{signup,login,logout}`, `GET /auth/me`.
  argon2id passwords (`accounts/security.py`), opaque session tokens stored as sha256 with a 30-day
  TTL, identical generic 401 for unknown-email vs wrong-password (no enumeration), duplicate-email 409.
- **Tenants + projects (S1 schema / S3 CRUD)** — migration `20260715_1200` creates the six tables;
  `src/vocky/app_api.py`: `GET /app/tenant`, `GET|POST /app/projects`, `GET /app/projects/{id}`,
  tenant-scoped, cross-tenant → 404 (never 403).
- **Per-project credentials (S1 schema / S4)** — `POST|GET|DELETE /app/projects/{id}/credentials`.
  `key = "vk_" + opaque`; plaintext returned once; only `token_hash` (sha256) + `token_prefix` stored;
  soft-revoke via `revoked_at`.
- **Mandatory `/api/*` credential auth + static token retired (S4)** — `ProjectCredentialAuthMiddleware`
  (`src/vocky/auth.py`) guards every `/api/*` request with no token arg and no open fallback;
  missing/malformed/unknown/revoked all → generic 401. `api_auth_token` field + `api_auth_token_value`
  removed from `config.py`; `.env.example` updated. Wired in `create_app()` (`src/vocky/app.py`)
  alongside the untouched `AdminBearerAuthMiddleware`.
- **Free / no billing** — no billing entities in schema or code.

No regressions, security gaps, or scope drift found. The ingest guard is correctly identity-only in
P2 (it does not thread project/tenant into `feedback_events` and does not stamp `last_used_at`), which
matches the confirmed P2/P3 boundary.

## Part B — Durable-doc consolidation

Versioned **8** docs, each `--source P2.REVIEW`, then ran `rebuild-docs` (regenerated `docs/current/*`).
`frontend`, `operations`, and `qa` left untouched.

| Doc | New version | Change |
| --- | --- | --- |
| product | `v0003_free_multi-tenant_saas_core_...` | Evolved: free multi-tenant SaaS direction; dropped the multi-tenant / SaaS-account / billing non-goals; added accounts/tenancy model, `/auth` + `/app` surfaces, mandatory per-project `/api/*` auth, and terminology. |
| architecture | `v0003_add_identity_tenancy_layer_...` | Evolved: new "Identity and Tenancy Layer" section (route groups + `accounts/` domain + tenant isolation + P2/P3 boundary); `ProjectCredentialAuthMiddleware`; removed `VOCKY_API_AUTH_TOKEN` from the config surface; updated MVP boundaries to multi-tenant. |
| api | `v0003_add_account_auth_..._mandatory_per-project_credential_auth_on_api` | Evolved: new contracts for Account Auth (`/auth/*`), Control-Plane tenant/projects and credentials (`/app/*`), and the mandatory `/api/*` Credential Auth Model; rewrote every `/api/*` auth/error block off the retired static token. |
| experience | `v0003_integrate_via_signup_..._authorization_bearer_on_api` | Evolved: new "Onboarding: Get a Project Credential" flow (signup → project → mint `vk_`); replaced the optional-static-token curl guidance with mandatory `vk_` bearer usage. |
| data | `v0002_accounts_and_tenancy_schema_...` | Authored: the six accounts/tenancy tables (columns/constraints/FKs/indexes) + migration `20260715_1200`; points to architecture.md for the feedback tables. |
| backend | `v0002_accounts_domain_package_...` | Authored: `src/vocky/accounts/` triad, `require_user`/`AuthContext`/`AuthError`, security primitives, `auth_api`/`app_api` route modules + app wiring + config change. |
| security | `v0002_argon2id_passwords_..._mandatory_ingest_auth_no_enumeration` | Authored: argon2id passwords, hashed opaque session tokens (30-day TTL), mint-once hashed `vk_` credentials + soft-revoke, mandatory ingest auth, no enumeration, tenant isolation, secret-exposure discipline. |
| decisions | `v0002_p2_auth-model_and_tenancy-shape_decisions_...` | Authored: 7 P2 decisions (opaque DB tokens over JWT/OAuth; multi-tenant solo-owner; `/app` vs `/api` split; strictly-mandatory ingest auth; 404-not-403 isolation; identity-only capture boundary; free/no billing). |

All lingering `VOCKY_API_AUTH_TOKEN` mentions in the consolidated docs are explicit "retired / deferred
to P4" notes, not live integration guidance.

## Deviations from plan.md

None. Followed Part A → Part B exactly and versioned the 8 docs named in the plan; wrote only
`docs/`, `phase.md`, and this `result.md`. Did not touch source, did not commit, did not run
`review-phase`/`finish-slice`/`set-*-status`.
