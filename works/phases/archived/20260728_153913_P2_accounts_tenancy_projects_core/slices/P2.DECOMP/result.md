# Result — P2.DECOMP (decomposition)

## What was created

Four bare middle slices for phase P2, each holding only `slice.json` (no `plan.md` pre-filled),
ordered before `P2.REVIEW`, in a strict S1→S4 dependency chain:

| Slice | Name | Kind | Risk | Order | depends_on |
|---|---|---|---|---|---|
| `P2.S1` | Identity & tenancy data model + persistence | implementation | medium | 1 | — |
| `P2.S2` | Account auth: signup / login / session tokens + user-auth guard | implementation | high | 2 | P2.S1 |
| `P2.S3` | Tenants & projects account-scoped API (CRUD) | implementation | medium | 3 | P2.S2 |
| `P2.S4` | Per-project credentials + swap public ingest auth | implementation | high | 4 | P2.S3 |

Created via `python3 scripts/workflow.py new-slice ...` exactly as specified in `plan.md`.

`phase.md` seeded: **Decomposition** (breakdown + rationale for the 4-way split and the chain),
**Findings & Notes** (the four operator-confirmed design decisions + reuse pointers), and a new
**Doc impact** list enumerating the seven docs `P2.REVIEW` will consolidate (product,
architecture, api, data, backend, security, decisions).

## Validation

- `python3 scripts/workflow.py validate` → **passed** (run after creating all four slices).
- `python3 scripts/workflow.py next` → current `P2.DECOMP`, next `P2.S1`; backlog shows
  P2.S1..P2.S4 as `todo` with the correct kinds/risks/order, all ahead of `P2.REVIEW`.
- Confirmed each new slice folder contains **only** `slice.json` (no `plan.md`).
- Confirmed each `slice.json`: kind=implementation; risks medium/high/medium/high; orders 1–4;
  depends_on chained S1←S2←S3←S4; all status `todo`.

## Deviations

None — slices, risks, order, and dependency chain match `plan.md` exactly.

## Risks / uncertainty surfaced to the orchestrator

- **P2.S1 risk (medium vs high):** the plan itself flags S1 as load-bearing schema and invites a
  bump to `high` at plan time. Created at `medium` per the literal spec; the orchestrator may
  bump one tier up when it plans S1 if the six-table migration + new domain package warrant it.
- **S4 is the sharpest boundary change:** it swaps the public ingest auth model and retires
  `VOCKY_API_AUTH_TOKEN`, and must update the existing `/api/feedback` tests to a project-credential
  fixture. Kept at `high`. Its scope is deliberately identity-only — no `project_id` on
  `feedback_events` (that is P3) and admin auth untouched (that is P4) — worth re-confirming when
  S4 is planned so scope does not creep.
