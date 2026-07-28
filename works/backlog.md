# Backlog

> Generated dashboard. Do not put detailed task context here; edit phase/slice/deferred folders instead.
> Status box: `[x]` done · `[~]` pending — waiting on operator · `[r]` ready — plan approved, awaiting execution · `[ ]` open/in progress.

## Pointer

- Current phase: `P10`
- Current slice: `P10.S4`
- Next slice: `P10.S5`
- Waiting on operator: `none`
- Open deferred jobs: `6`
- Rebuilt at: `2026-07-28T23:08:30+09:00`

## Active Phases

| Phase | Status | Review | Name | Current Slice | Path |
|---|---|---|---|---|---|
| [x] `P6` | `done` | `pass` | Landing Page, Webpage & Production Deploy | `none` | `works/phases/active/P6` |
| [ ] `P10` | `planned` | `pending` | Accounts v2: orgs, org-level keys & default project | `P10.S4` | `works/phases/active/P10` |
| [ ] `P11` | `planned` | `pending` | Frictionless onboarding: working install, env-var quickstart, agent skill on the landing | `P11.DECOMP` | `works/phases/active/P11` |
| [ ] `P12` | `planned` | `pending` | Production launch & hardening: bring-up, rate limits, CI tests, QA doc | `P12.DECOMP` | `works/phases/active/P12` |

## Phase P6: Landing Page, Webpage & Production Deploy

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P6.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P6/slices/P6.DECOMP` |
| [x] `P6.S1` | `done` | Admin-UI removal | `implementation` | `works/phases/active/P6/slices/P6.S1` |
| [x] `P6.S2` | `done` | Landing/site metadata & production origin | `implementation` | `works/phases/active/P6/slices/P6.S2` |
| [x] `P6.S3` | `done` | CSP + HSTS security headers | `implementation` | `works/phases/active/P6/slices/P6.S3` |
| [x] `P6.S4` | `done` | Web production Dockerfile | `implementation` | `works/phases/active/P6/slices/P6.S4` |
| [x] `P6.S5` | `done` | Production compose + env template | `implementation` | `works/phases/active/P6/slices/P6.S5` |
| [x] `P6.S6` | `done` | Edge nginx vhost (vocky.conf) | `implementation` | `works/phases/active/P6/slices/P6.S6` |
| [x] `P6.S7` | `done` | Deploy + rollback scripts | `implementation` | `works/phases/active/P6/slices/P6.S7` |
| [x] `P6.S8` | `done` | CI production-deploy chain | `implementation` | `works/phases/active/P6/slices/P6.S8` |
| [x] `P6.S9` | `done` | PyPI packaging + publish | `implementation` | `works/phases/active/P6/slices/P6.S9` |
| [x] `P6.REVIEW` | `done` | phase review | `review` | `works/phases/active/P6/slices/P6.REVIEW` |

## Phase P10: Accounts v2: orgs, org-level keys & default project

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P10.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P10/slices/P10.DECOMP` |
| [x] `P10.S1` | `done` | Schema: projects UNIQUE(tenant_id,name), credential tenant_id + nullable project_id, signup default-project provisioning | `implementation` | `works/phases/active/P10/slices/P10.S1` |
| [x] `P10.S2` | `done` | Org-scoped enforcement landed dark: every credential-derived project filter becomes org-aware | `implementation` | `works/phases/active/P10/slices/P10.S2` |
| [x] `P10.S3` | `done` | Org-key mint surface: /app/credentials routes + tenant-aware resolver (turns org keys on) | `implementation` | `works/phases/active/P10/slices/P10.S3` |
| [ ] `P10.S4` | `todo` | Web app: dashboard org-keys panel, nullable project_id type, Workspace to Org copy | `implementation` | `works/phases/active/P10/slices/P10.S4` |
| [ ] `P10.S5` | `todo` | CLI parity: org-level key mint/list/revoke plus Workspace to Org wording | `implementation` | `works/phases/active/P10/slices/P10.S5` |
| [ ] `P10.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P10/slices/P10.REVIEW` |

## Phase P11: Frictionless onboarding: working install, env-var quickstart, agent skill on the landing

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [ ] `P11.DECOMP` | `todo` | decompose phase | `decomposition` | `works/phases/active/P11/slices/P11.DECOMP` |
| [ ] `P11.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P11/slices/P11.REVIEW` |

## Phase P12: Production launch & hardening: bring-up, rate limits, CI tests, QA doc

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [ ] `P12.DECOMP` | `todo` | decompose phase | `decomposition` | `works/phases/active/P12/slices/P12.DECOMP` |
| [ ] `P12.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P12/slices/P12.REVIEW` |
