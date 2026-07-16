# Backlog

> Generated dashboard. Do not put detailed task context here; edit phase/slice/deferred folders instead.
> Status box: `[x]` done · `[~]` pending — waiting on operator · `[r]` ready — plan approved, awaiting execution · `[ ]` open/in progress.

## Pointer

- Current phase: `P8`
- Current slice: `P8.S1`
- Next slice: `P8.S2`
- Waiting on operator: `none`
- Open deferred jobs: `4`
- Rebuilt at: `2026-07-17T00:26:26+09:00`

## Active Phases

| Phase | Status | Review | Name | Current Slice | Path |
|---|---|---|---|---|---|
| [x] `P1` | `done` | `pass` | Relicense & Agent-Capture Retirement | `none` | `works/phases/active/P1` |
| [x] `P2` | `done` | `pass` | Accounts, Tenancy & Projects Core | `none` | `works/phases/active/P2` |
| [x] `P3` | `done` | `pass` | Feedback API v2, Search & Usage Monitoring | `none` | `works/phases/active/P3` |
| [x] `P7` | `done` | `pass` | Agent-Capture Revival (MCP write-only) | `none` | `works/phases/active/P7` |
| [x] `P4` | `done` | `pass` | Web App: Tenant Dashboard & Project Pages | `none` | `works/phases/active/P4` |
| [ ] `P8` | `planned` | `pending` | Design Gate: Brand, App UI & Landing | `P8.S1` | `works/phases/active/P8` |
| [ ] `P5` | `planned` | `pending` | CLI & Agent-First Onboarding | `P5.DECOMP` | `works/phases/active/P5` |
| [ ] `P6` | `planned` | `pending` | Landing Page, Webpage & Production Deploy | `P6.DECOMP` | `works/phases/active/P6` |

## Phase P1: Relicense & Agent-Capture Retirement

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P1.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P1/slices/P1.DECOMP` |
| [x] `P1.S1` | `done` | Relicense to MIT | `implementation` | `works/phases/active/P1/slices/P1.S1` |
| [x] `P1.S2` | `done` | Retire MCP/agent-capture from the system | `implementation` | `works/phases/active/P1/slices/P1.S2` |
| [x] `P1.S3` | `done` | Scrub MCP from README & ancillary docs | `implementation` | `works/phases/active/P1/slices/P1.S3` |
| [x] `P1.F1` | `done` | Restore REST target_type help string in docs.json | `fix` | `works/phases/active/P1/slices/P1.F1` |
| [x] `P1.REVIEW` | `done` | phase review | `review` | `works/phases/active/P1/slices/P1.REVIEW` |

## Phase P2: Accounts, Tenancy & Projects Core

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P2.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P2/slices/P2.DECOMP` |
| [x] `P2.S1` | `done` | Identity & tenancy data model + persistence | `implementation` | `works/phases/active/P2/slices/P2.S1` |
| [x] `P2.S2` | `done` | Account auth: signup / login / session tokens + user-auth guard | `implementation` | `works/phases/active/P2/slices/P2.S2` |
| [x] `P2.S3` | `done` | Tenants & projects account-scoped API (CRUD) | `implementation` | `works/phases/active/P2/slices/P2.S3` |
| [x] `P2.S4` | `done` | Per-project credentials + swap public ingest auth | `implementation` | `works/phases/active/P2/slices/P2.S4` |
| [x] `P2.REVIEW` | `done` | phase review | `review` | `works/phases/active/P2/slices/P2.REVIEW` |

## Phase P3: Feedback API v2, Search & Usage Monitoring

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P3.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P3/slices/P3.DECOMP` |
| [x] `P3.S1` | `done` | Project-scope foundation: project_id on feedback + capture threading + last_used stamps | `implementation` | `works/phases/active/P3/slices/P3.S1` |
| [x] `P3.S2` | `done` | /api project-scoped feedback review + manage (project-credential authed) | `implementation` | `works/phases/active/P3/slices/P3.S2` |
| [x] `P3.S3` | `done` | /app cross-project feedback read + multilingual Postgres search | `implementation` | `works/phases/active/P3/slices/P3.S3` |
| [x] `P3.S4` | `done` | Usage monitoring: per-tenant/project derived metrics + surfaced last-used | `implementation` | `works/phases/active/P3/slices/P3.S4` |
| [x] `P3.REVIEW` | `done` | phase review | `review` | `works/phases/active/P3/slices/P3.REVIEW` |

## Phase P7: Agent-Capture Revival (MCP write-only)

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P7.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P7/slices/P7.DECOMP` |
| [x] `P7.S1` | `done` | MCP transport foundation: mcp dep, FastMCP server, /mcp mount, session_manager lifespan | `implementation` | `works/phases/active/P7/slices/P7.S1` |
| [x] `P7.S2` | `done` | capture_feedback write tool: per-project vk_ credential auth + capture-pipeline integration + integration test | `implementation` | `works/phases/active/P7/slices/P7.S2` |
| [x] `P7.REVIEW` | `done` | phase review | `review` | `works/phases/active/P7/slices/P7.REVIEW` |

## Phase P4: Web App: Tenant Dashboard & Project Pages

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P4.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P4/slices/P4.DECOMP` |
| [x] `P4.S1` | `done` | App scaffold + design-system foundation | `implementation` | `works/phases/active/P4/slices/P4.S1` |
| [x] `P4.S2` | `done` | Auth + BFF proxy + authenticated app shell | `implementation` | `works/phases/active/P4/slices/P4.S2` |
| [x] `P4.S3` | `done` | Tenant dashboard: projects + create + tenant usage | `implementation` | `works/phases/active/P4/slices/P4.S3` |
| [x] `P4.S4` | `done` | Project detail: info + credentials + project usage | `implementation` | `works/phases/active/P4/slices/P4.S4` |
| [x] `P4.S5` | `done` | Cross-project feedback list + Korean-safe search + detail | `implementation` | `works/phases/active/P4/slices/P4.S5` |
| [x] `P4.REVIEW` | `done` | phase review | `review` | `works/phases/active/P4/slices/P4.REVIEW` |

## Phase P8: Design Gate: Brand, App UI & Landing

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [x] `P8.DECOMP` | `done` | decompose phase | `decomposition` | `works/phases/active/P8/slices/P8.DECOMP` |
| [ ] `P8.S1` | `todo` | foundations cards + hi2vi reference card | `implementation` | `works/phases/active/P8/slices/P8.S1` |
| [ ] `P8.S2` | `todo` | component cards: complete the set | `implementation` | `works/phases/active/P8/slices/P8.S2` |
| [ ] `P8.S3` | `todo` | app section cards: auth, shell, dashboard | `implementation` | `works/phases/active/P8/slices/P8.S3` |
| [ ] `P8.S4` | `todo` | app section cards: project detail, feedback list, feedback detail | `implementation` | `works/phases/active/P8/slices/P8.S4` |
| [ ] `P8.S5` | `todo` | landing section cards with placeholder copy slots | `implementation` | `works/phases/active/P8/slices/P8.S5` |
| [ ] `P8.S6` | `todo` | manifest + tokens pre-flight, push canvas to claude.ai | `implementation` | `works/phases/active/P8/slices/P8.S6` |
| [ ] `P8.S7` | `todo` | design gate: hand off to the Claude Design session | `implementation` | `works/phases/active/P8/slices/P8.S7` |
| [ ] `P8.S8` | `todo` | decompose the signed-off implementation | `decomposition` | `works/phases/active/P8/slices/P8.S8` |
| [ ] `P8.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P8/slices/P8.REVIEW` |

## Phase P5: CLI & Agent-First Onboarding

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [ ] `P5.DECOMP` | `todo` | decompose phase | `decomposition` | `works/phases/active/P5/slices/P5.DECOMP` |
| [ ] `P5.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P5/slices/P5.REVIEW` |

## Phase P6: Landing Page, Webpage & Production Deploy

| Slice | Status | Name | Kind | Path |
|---|---|---|---|---|
| [ ] `P6.DECOMP` | `todo` | decompose phase | `decomposition` | `works/phases/active/P6/slices/P6.DECOMP` |
| [ ] `P6.REVIEW` | `todo` | phase review | `review` | `works/phases/active/P6/slices/P6.REVIEW` |
