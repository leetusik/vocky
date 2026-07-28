# P4.DECOMP — Result

Decomposed the Web App phase into 5 bare middle-slice folders and seeded `phase.md`. No application code, no slice `plan.md`, no `doc-new-version`, no commits.

## Research verification (against the current tree)

Spot-checked the plan's research — all present, no drift:

- **vocky endpoints (Starlette `Route` lists, not FastAPI routers):** `auth_api.py` (`/auth/signup|login|logout|me`), `app_api.py` (`/app/tenant`, `/app/projects` GET/POST, `/app/projects/{id}`, `/app/projects/{id}/credentials` POST/GET, `.../{cid}` DELETE), `app_feedback_api.py` (`/app/feedback`, `/app/feedback/{id}`, `.../attachments/{aid}`), `usage_api.py` (`/app/usage`, `/app/projects/{id}/usage`). Session guard `accounts/auth.py::require_user` present (line 61).
- **Retiring admin UI:** `src/vocky/admin_ui.py` + `src/vocky/admin_assets/*` present (mounted in `app.py`).
- **hi2vi_web template (`~/projects/personal/hi2vi_web`):** `src/app/globals.css`, `src/components/ui/*` (button/card/section/field/badge/grid — no data-table, as the plan assumes), `src/lib/utils.ts`, `src/lib/agent/auth.ts`, `content-agent/{console.tsx,api.ts,hooks.ts}`, `design/canvas/`, `next.config.ts`/`Dockerfile`/`deploy/` all present.

Kept the 5-slice shape (did not collapse S3+S4): project-detail carries its own distinct API set plus the security-sensitive show-once credential-mint UX, so it is not small enough to fold into the dashboard.

## Slices created

| ID | Name | Kind | Risk | Order | Depends |
|----|------|------|------|-------|---------|
| P4.S1 | App scaffold + design-system foundation | implementation | medium | 1 | — |
| P4.S2 | Auth + BFF proxy + authenticated app shell | implementation | high | 2 | P4.S1 |
| P4.S3 | Tenant dashboard: projects + create + tenant usage | implementation | medium | 3 | P4.S2 |
| P4.S4 | Project detail: info + credentials + project usage | implementation | medium | 4 | P4.S2 |
| P4.S5 | Cross-project feedback list + Korean-safe search + detail | implementation | medium | 5 | P4.S2 |

Each folder holds **only `slice.json`** (no `plan.md`/`result.md` — verified). Shape: foundation chain S1 → S2, then fan-out S3/S4/S5 (each depends only on S2). One `high` (S2, the auth/BFF boundary); the rest `medium`; no `low`.

## phase.md sections seeded

- **Context** — greenfield-frontend framing; BFF / subdir / design-gate decisions; P4 replaces the retiring admin UI; session-token client of `/auth/*`+`/app/*` only.
- **Decomposition** — foundation-chain + fan-out intro, the five per-slice bullets (`ID — Name · risk · order · depends_on` + touch-list + `_Rationale:_`), and the "Why 5, not 4" split-rationale paragraph.
- **Findings & Notes** — Decisions **D-P4-1/2/3**; Implementation anchors (vocky API files + route line-numbers, retiring admin UI, hi2vi_web template paths).
- **Constraints** — session-token-only, BFF boundary, read+search-only feedback, 404-never-403, Korean-safe `?q`, derived/30-day usage, show-once credential, `@theme`/no-dark-mode, defer heavy design gate + deploy to P6, DECOMP writes no code.
- **Open Questions** — admin-UI retirement timing (P4 vs P6, leaning P6); vocky palette vs. reused hi2vi_web tokens; deployed domain vs. local dev; deferred-job D2 intersection.
- **Doc impact** — started the running list (`frontend.md` fresh v0002, `architecture.md`, `experience.md`, `decisions.md`, `operations.md`, possibly `product.md`) + a "landed changes" subheading for each middle slice to append to.

## Validation

| Command | Outcome |
|---------|---------|
| `python3 scripts/workflow.py validate` | **passed** (`Workflow validation passed.`) |
| `python3 scripts/workflow.py next` | `next_slice=P4.S1` — P4.S1 (order 1) is the next active slice; DECOMP stays `in_progress` because only the orchestrator transitions it |

Backlog now lists P4.S1–S5 (todo) + P4.REVIEW with the risk/order/depends above; `slice.json` metadata confirmed for all five.

## Deviations

None. Kept the 5-slice shape as planned; ran the exact `new-slice` commands; no `web/` code, no slice `plan.md`, no `docs/versions/*`, no commit.
