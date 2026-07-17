# P8.DECOMP — result

Created P8's seven middle slices as **bare folders** and recorded the breakdown, the split/risk
rationale, and the new findings in `phase.md`. No cards, no code, no other slice's `plan.md`.

## What was created

Exactly the shape `plan.md` specified — `intent.md`'s **seed → brief → gate → synthesis**, round 1 only:

| Slice | Kind | Risk | Order | Depends on |
|---|---|---|---|---|
| `P8.S1` Frozen baseline render of the 6 shipped surfaces | `implementation` | `medium` | 1 | — |
| `P8.S2` DS cards: foundations, DataTable, `Reference — hi2vi vibe`; drop the fictional placeholder | `implementation` | `high` | 2 | — |
| `P8.S3` Surface mirror cards A: app shell, login/signup, dashboard | `implementation` | `high` | 3 | `P8.S1` |
| `P8.S4` Surface mirror cards B: project detail, feedback list, feedback detail | `implementation` | `high` | 4 | `P8.S1` |
| `P8.S5` Gate brief card + `_ds_manifest.json` regen + P6→P8 source fixes | `implementation` | `high` | 5 | `P8.S2`, `P8.S3`, `P8.S4` |
| `P8.S6` **The design gate: push → STOP → read-back** | **`co-work`** | **`high`** | 6 | `P8.S5` |
| `P8.S7` Synthesis: capture the spec into `phase.md` + write the SIGNOFF | `implementation` | `high` | 7 | `P8.S6` |

Slice names are terse recognisable renderings of the plan's intent (ASCII-safe in `slice.json` /
`backlog.md`; the em-dash/arrow forms live in the `phase.md` table).

## Validation

| Command | Outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **passed clean** — `Workflow validation passed.` (this is the check that catches the `depends_on` trap) |
| `python3 scripts/workflow.py next` | **`next_slice=P8.S1`** — correct |
| `works/backlog.md` | P8 renders 7 middle slices at orders 1–7, `P8.S6` as `co-work`, none `low` |
| Folder contents check | each of `P8.S1`–`P8.S7` holds **`slice.json` only** — no pre-filled `plan.md` |
| `slice.json` dump | kinds/risks/orders/deps match the table exactly; `P8.S5` deps = `['P8.S2', 'P8.S3', 'P8.S4']` (a real 3-element array) |

## The `--depends-on` trap — avoided

The first `P8.DECOMP` died here. Confirmed `action="append"` at `scripts/workflow.py:1066` **before**
creating anything, then repeated the flag per dependency:

```
--depends-on P8.S2 --depends-on P8.S3 --depends-on P8.S4
```

`P8.S5` stored three real deps and `validate` passed. A comma-separated string would have stored one
literal dep and failed with `missing dependency`.

## Constraints honored

- **Zero brand decisions.** Nothing here proposes a palette, a type direction, or landing copy. The
  decomposition only *routes* design questions to the gate — it answers none.
- **No landing mirror cards were sliced.** The landing does not exist in code, so authoring
  hero/features/pricing/footer cards would be invention, not mirroring. It reaches the session through
  the brief **as questions**. This is deliberate and recorded under *What is deliberately NOT sliced* —
  not a coverage gap against `intent.md`'s "landing sections".
- **`S6` is `co-work`/`high` and is flagged NEVER-dispatched**; round 1 only, no round 2, no apply
  slices (P9 owns the apply).
- **Bare folders only** — no middle slice's `plan.md` was pre-filled.
- **Nothing rated `low`** — flex mode makes `medium`≡`high` in cost, and the constraint these slices can
  most easily break (zero brand decisions) is exactly what a literal plan-follower crosses unnoticed.
- **No `doc-new-version`** — docs are versioned once, at `P8.REVIEW`. No status transitions, no commits;
  `new-slice` was the only workflow command run (plus read-only `validate` / `next`).

## `phase.md` updates

- **Decomposition** (was empty) — filled with the table, the split rationale, the risk rationale
  (incl. why nothing is `low`), and the two deliberate exclusions with their reasons. Kept the two
  binding v12 rules and noted that both survived into the shape.
- **Findings & Notes** — appended one new subsection, *Established at `P8.DECOMP` (2026-07-17)*, with
  only what this slice newly establishes. Harvested facts were **not** re-derived or restated.

## Doc impact

**None.** This slice changed no durable truth — it created workflow state and phase notes only. The
phase's pre-recorded *Doc impact* entry (`docs/current/` still calls the design gate "P6") already
covers what `P8.REVIEW` must consolidate; nothing was added to it.

## Deviations from `plan.md`

**None.** The shape, kinds, risks, orders, and dependencies are exactly as specified.

## For the next slice

`P8.S1` is selected. The two traps its plan must resolve are now in `phase.md` → *Established at
`P8.DECOMP`*: **self-hosted fonts** (a curl'd page references `/_next/static/media/*.woff2`, which dies
with the server — a silently system-font "frozen" render) and **auth** (the 6 surfaces need a POSTed
login and a kept session cookie). Its output lands at **`web/design/baseline/`**, repo-only — never
pushed as canvas cards.
