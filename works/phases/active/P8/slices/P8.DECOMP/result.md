# Result — `P8.DECOMP`

Decomposed P8 per `plan.md`. Created **eight middle slices as bare folders** and seeded `phase.md` with the
breakdown, the handed-down findings, the four operator rulings as durable constraints, and the gate's open
questions. Designed nothing; wrote no code.

## What was created

| Slice | Order | Kind | Risk | Depends on |
| --- | --- | --- | --- | --- |
| `P8.S1` foundations cards + hi2vi reference card | 1 | implementation | `medium` | — |
| `P8.S2` component cards: complete the set | 2 | implementation | `medium` | — |
| `P8.S3` app section cards: auth, shell, dashboard | 3 | implementation | `medium` | — |
| `P8.S4` app section cards: project detail, feedback list, feedback detail | 4 | implementation | `medium` | — |
| `P8.S5` landing section cards with placeholder copy slots | 5 | implementation | `high` | `P8.S2` |
| `P8.S6` manifest + tokens pre-flight, push canvas to claude.ai | 6 | implementation | `high` | `P8.S1`–`P8.S5` |
| `P8.S7` design gate: hand off to the Claude Design session | 7 | implementation | `high` | `P8.S6` |
| `P8.S8` decompose the signed-off implementation | 8 | **decomposition** | `high` | `P8.S7` |

`P8.REVIEW` already existed at `order 9999`; untouched. **No implementation slices for the post-gate work were
created** — that is `P8.S8`'s job, per the operator's two-stage-decomposition ruling. Every new folder contains
`slice.json` only; no `plan.md` was pre-filled.

Rationale for the sizing, the merge of pre-flight into the push, the S3/S4 split, and each risk rating is recorded
in `phase.md` → *Decomposition*.

## Risk ratings — the one judgment worth flagging

`executors.toml` sits at its default `flex` mode, where **`medium` and `high` are the same model and effort**
(opus @ `xhigh`); only `low` (sonnet) saves cost. So mid-vs-high here is **not** a cost decision — it is escalation
latitude. Nothing is rated `low`: the plan states card authoring is judgment work, and `low` routes to a literal
plan-follower. S1–S4 are `medium` (a real shipped surface to mirror ⇒ "correct" is checkable, and escalation is a
real safety valve if a finding proves stale); S5–S8 are `high` (S5 has no surface to mirror and sits exactly on the
structure-vs-brand line; S6 makes an irreversible `create_project` call; S7 is the gate briefing; S8 is
decomposition, which routes high regardless).

## Validation

| Command | Outcome |
| --- | --- |
| `python3 scripts/workflow.py validate` | **passed** — `Workflow validation passed.` (failed once first; see Deviations) |
| `python3 scripts/workflow.py next` | **passed** — `next_slice=P8.S1`, the first pre-gate slice |
| `python3 scripts/workflow.py rebuild` | **passed** — dashboards regenerated |
| `works/backlog.md` inspection | **passed** — lists `P8.S1`–`P8.S8` with the intended order/kind, plus the gate slice and the post-gate `decomposition` slice, and **no** implementation slices for post-gate work |
| Bare-folder check (`ls` each new slice dir) | **passed** — every new folder holds `slice.json` only |

## Deviations from `plan.md`

One, mechanical — no scope change.

**`--depends-on` is `action="append"`, not comma-separated.** `new-slice --depends-on P8.S1,P8.S2,P8.S3,P8.S4,P8.S5`
was accepted silently but stored the whole string as a *single* literal dependency, and `validate` then failed:

```
- missing dependency for P8.S6: P8.S1,P8.S2,P8.S3,P8.S4,P8.S5
```

Fixed by editing `works/phases/active/P8/slices/P8.S6/slice.json` to hold the five ids as separate array entries,
then `rebuild`; `validate` passes. This is slice metadata correction, not a status transition — no status field was
touched and no forbidden command was run. Recorded in `phase.md` → *Findings* so later slices (notably `P8.S8`,
which will call `new-slice` repeatedly) repeat the flag instead: `--depends-on A --depends-on B`.

## Doc impact

No durable-truth change in this slice. One note was **pre-recorded** in `phase.md`'s "Doc impact" list for
`P8.REVIEW`: `docs/current/` universally still calls the design gate "P6" (`frontend.md`, `decisions.md` D-P4-3,
`experience.md`, `architecture.md`, `product.md`), while P8 supersedes D-P4-3 and absorbs the landing design +
build, leaving P6 deploy-only. `web/design/canvas/README.md` and `_ds_manifest.json`'s `note` carry the same stale
"P6 gate" language, but those are **source** and are assigned to `P8.S6`.

## Notes for the orchestrator

- `P8.S7` is `kind: implementation` on purpose. `--kind` is free-form in the engine, but tier routing keys off
  `kind` + `risk`, so a novel kind (e.g. `gate`) would risk misrouting for no gain. It is a co-work gate despite
  the label: its executor returns `needs_operator`, and you set it `pending`.
- The phase's true size is unknown until the signoff, by operator ruling. `P8.S8` will extend the phase with the
  implementation slices; `P8.REVIEW` stays at `9999` and needs no renumbering.
