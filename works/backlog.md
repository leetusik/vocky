# Backlog

> Generated dashboard. Do not put detailed task context here; edit phase/slice/deferred folders instead.
> Status box: `[x]` done · `[~]` pending — waiting on operator · `[r]` ready — plan approved, awaiting execution · `[ ]` open/in progress.

## Pointer

- Current phase: `P12`
- Current slice: `P12.S3`
- Next slice: `P12.S6`
- Waiting on operator: `none`
- Open deferred jobs: `6`
- Rebuilt at: `2026-08-04T10:30:39+09:00`

## Active Phases

| Phase | Status | Review | Name | Current Slice | Path |
|---|---|---|---|---|---|
| [x] `P6` | `done` | `pass` | Landing Page, Webpage & Production Deploy | `none` | `works/phases/active/P6` |
| [x] `P10` | `done` | `pass` | Accounts v2: orgs, org-level keys & default project | `none` | `works/phases/active/P10` |
| [x] `P11` | `done` | `pass` | Frictionless onboarding: working install, env-var quickstart, agent skill on the landing | `none` | `works/phases/active/P11` |
| [ ] `P12` | `planned` | `pending` | Production launch & hardening: bring-up, rate limits, CI tests, QA doc | `P12.S3` | `works/phases/active/P12` |

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
| [x] `P10.S4` | `done` | Web app: dashboard org-keys panel, nullable project_id type, Workspace to Org copy | `implementation` | `works/phases/active/P10/slices/P10.S4` |
| [x] `P10.S5` | `done` | CLI parity: org-level key mint/list/revoke plus Workspace to Org wording | `implementation` | `works/phases/active/P10/slices/P10.S5` |
| [x] `P10.REVIEW` | `done` | phase review | `review` | `works/phases/active/P10/slices/P10.REVIEW` |

## Phase P11: Frictionless onboarding: working install, env-var quickstart, agent skill on the landing

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P11.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P11/slices/P11.DECOMP` |
| [x] `P11.S1` | `done` | Landing hero honesty: nested source.product + real vk_ key shape | `implementation` | `works/phases/active/P11/slices/P11.S1` |
| [x] `P11.S2` | `done` | CLI: VOCKY_API_TOKEN resolution + vocky capture over /api/feedback | `implementation` | `works/phases/active/P11/slices/P11.S2` |
| [x] `P11.S3` | `done` | curl \| bash installer: web/public/install.sh | `implementation` | `works/phases/active/P11/slices/P11.S3` |
| [x] `P11.S4` | `done` | Canonical end-user SKILL.md, served byte-copy, parity script + first CI workflow | `implementation` | `works/phases/active/P11/slices/P11.S4` |
| [x] `P11.S5` | `done` | Design round 02: hero install row, agent env-var quickstart, skill-on-landing | `co-work` | `works/phases/active/P11/slices/P11.S5` |
| [x] `P11.DECOMP2` | `done` | Decompose the build from the landed design | `decomposition` | `works/phases/active/P11/slices/P11.DECOMP2` |
| [x] `P11.S6` | `done` | Primitives + copy: Snippet, Trap, pure copy helper, section-ids, landing.ts blocks | `implementation` | `works/phases/active/P11/slices/P11.S6` |
| [x] `P11.S7` | `done` | Hero install row + nav (one new link, nav order per build-prompt 2) | `implementation` | `works/phases/active/P11/slices/P11.S7` |
| [x] `P11.S8` | `done` | AgentQuickstart section + ReadingList + page.tsx insertion | `implementation` | `works/phases/active/P11/slices/P11.S8` |
| [x] `P11.S9` | `done` | SkillSection + SkillPreview server read + page.tsx insertion | `implementation` | `works/phases/active/P11/slices/P11.S9` |
| [x] `P11.S10` | `done` | Design-fidelity pass: acceptance checks, no-JS, a11y and reduced-motion floors | `implementation` | `works/phases/active/P11/slices/P11.S10` |
| [x] `P11.REVIEW` | `done` | phase review | `review` | `works/phases/active/P11/slices/P11.REVIEW` |

## Phase P12: Production launch & hardening: bring-up, rate limits, CI tests, QA doc

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P12.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P12/slices/P12.DECOMP` |
| [x] `P12.S1` | `done` | Decide the fate of /admin/api/* and VOCKY_ADMIN_AUTH_TOKEN | `implementation` | `works/phases/active/P12/slices/P12.S1` |
| [x] `P12.S2` | `done` | Repo hygiene sweep: retired token refs, prettier debt, vestigial design-token names | `implementation` | `works/phases/active/P12/slices/P12.S2` |
| [ ] `P12.S3` | `todo` | Rate-limit the public /auth/* surface (D5) | `implementation` | `works/phases/active/P12/slices/P12.S3` |
| [ ] `P12.S6` | `todo` | Extend ci.yml with a Postgres-backed pytest job | `implementation` | `works/phases/active/P12/slices/P12.S6` |
| [ ] `P12.S4` | `todo` | Production bring-up at vocky.hi2vi.com (operator-gated) | `co-work` | `works/phases/active/P12/slices/P12.S4` |
| [ ] `P12.S5` | `todo` | Postgres backups, log rotation and basic metrics | `implementation` | `works/phases/active/P12/slices/P12.S5` |
| [ ] `P12.S7` | `todo` | Author docs/current/qa.md | `implementation` | `works/phases/active/P12/slices/P12.S7` |
| [ ] `P12.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P12/slices/P12.REVIEW` |
