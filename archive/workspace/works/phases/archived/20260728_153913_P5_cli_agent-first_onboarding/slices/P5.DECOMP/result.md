# Result — P5.DECOMP

Decomposed phase P5 ("CLI & Agent-First Onboarding") into five bare middle slices and seeded the phase notebook. No source, docs, or middle-slice `plan.md` was written; nothing was committed; no slice/phase status was transitioned.

## What I did

1. **Created five bare middle-slice folders** via `new-slice` (the only workflow mutation run), each holding only its `slice.json`:

   | Slice | Order | Kind | Risk | Depends on |
   |-------|-------|------|------|-----------|
   | P5.S1 | 1 | implementation | medium | P5.DECOMP |
   | P5.S2 | 2 | implementation | medium | P5.S1 |
   | P5.S3 | 3 | implementation | medium | P5.S1 |
   | P5.S4 | 4 | implementation | medium | P5.S1 |
   | P5.S5 | 5 | implementation | medium | P5.S2 |

   All five sit between `P5.DECOMP` (order 0) and `P5.REVIEW`, are `status: todo`, and carry the exact `--kind`/`--risk`/`--order`/`--depends-on` the plan specified. Verified each folder contains only `slice.json` (no pre-filled `plan.md`).

2. **Seeded `works/phases/active/P5/phase.md`** with:
   - **Context** — CLI is a pure client (no backend change); `smoke.py` headless reference; stale README is the public "Docs" target; no `llms.txt` yet; not a design-gate phase.
   - **Operator decisions** — the 5 confirmed decisions recorded verbatim (auth flow = direct email+password; `vocky` CLI name + server rename to `vocky-server`; Typer as a direct dep; onboarding + feedback-read scope; distribution via console script + `uv tool`/`uvx`, PyPI to P6).
   - **Decomposition** — slice table + rationale + per-slice intents (S1–S5), explicitly noting the middle-slice `plan.md`s must NOT be pre-filled.
   - **Findings & Notes** — the full API contract the CLI drives, packaging facts, the missing home-dir config convention, the server-rename blast radius, UX copy to mirror, and the docs gap.
   - **Constraints** — pure client / no backend change; `uv` conventions; token file `0600`; keep tests small; leave stale packaged admin docs (`admin_assets/docs.json`) to P6; docs versioned once at REVIEW.
   - **Doc impact** — empty running list for middle slices to append to.

## Validation

- `python3 scripts/workflow.py validate` → **passed** (state integrity: five `todo` slices P5.S1..P5.S5 between DECOMP and REVIEW with the right orders/kinds/risks; `phase.md` seeded).

## Deviations from plan

None. Ran the five `new-slice` commands exactly as listed and seeded `phase.md` with every section the plan called for.

## Cross-slice notes

Cross-slice context lives in `phase.md` (Findings & Notes, Constraints, Decomposition slice intents, Doc impact). Key reminders for later slices:
- S1 is the spine (Typer app + config/credential store + shared httpx client + packaging rename); S2/S3/S4 layer command groups on it; S5 (docs) must describe the finished surface and appends "Doc impact" notes rather than versioning docs.
- Never modify the backend; the CLI authenticates to `/app/*` with the **session** token and only mints `vk_` keys for the user (which authorize `/api/*` + `/mcp`).
