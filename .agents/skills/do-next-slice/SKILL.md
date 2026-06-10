---
name: do-next-slice
description: Continue the active phase by completing exactly one slice, then stop.
---

# do-next-slice

Run `python3 scripts/workflow.py next`, then read `AGENTS.md` (or `CLAUDE.md`), `docs/current/*.md` as needed, `docs/index.json`, `works/state.json`, `works/backlog.md`, the selected slice folder, and the phase's `phase.md` (the phase notebook — accumulated decomposition, findings, and cross-slice notes).

Work exactly one slice:

1. If the selected slice is `todo`, run `python3 scripts/workflow.py start-slice <slice_id>`.
2. Fill this slice's own `plan.md` before implementing — Goal, Scope, Milestones, and Validation are required, not optional; pull relevant context from `phase.md`. If the operator passed any note or extra instructions with the command, record it verbatim in `plan.md` under a `## Operator Input (verbatim)` heading. Never pre-fill another slice's `plan.md`.
3. Implement the slice.
4. For durable doc changes, run `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source <slice_id>`, edit only the returned `edit_path`, then run `python3 scripts/workflow.py rebuild-docs`.
5. Record validation commands, created doc versions, and outcome in `result.md`, and append any durable cross-slice notes (decisions, findings, gotchas) to the phase's `phase.md` so later slices can build on them.
6. Mark the slice done with `python3 scripts/workflow.py finish-slice <slice_id>` only when complete.
7. Run `python3 scripts/workflow.py validate`.
8. Commit by default: group the slice's pending changes into focused `type(scope): summary` commit(s) following the Commit Convention. Do not branch unless the operator asks; never push.

When the selected slice is a decomposition (`kind: decomposition`), step 3 ("implement") means decomposing the phase, not writing code:

- Create the middle slices with `python3 scripts/workflow.py new-slice --phase <P> --slice <P>.S<n> --name "..."` (add `--kind`, `--risk`, `--order`, `--depends-on` as needed). Create the slices **only** — do not pre-fill their `plan.md`; each slice fills its own when it runs.
- Record the slice breakdown (what each slice covers and why) plus any research or findings in the phase's `phase.md`, so later slices share that context.

When the selected slice is a phase review (`kind: review`), step 3 ("implement") means running the review, not writing code:

- Invoke the read-only `phase-reviewer` subagent for the phase; record its verdict and the review outcome in `result.md` (the machine verdict is also persisted to `phase.json` by `review-phase`). (In Codex, follow the `review-phase` skill checklist instead.)
- Record the verdict: `python3 scripts/workflow.py review-phase <P> --verdict pass|changes_requested|blocked --reviewer phase-reviewer --note "..."`.
- On `pass`: run `finish-slice <slice_id>`. A passing review marks the phase `done` but it **stays in `active/`** — archiving is a separate, manual step, so do **not** archive now. Archive later when you choose: `archive-all` once every active phase is done, `rotate-backlog` to archive just the done phases while others continue, or `archive-phase <P>` for one phase.
- On `changes_requested`: create fix slices (`python3 scripts/workflow.py new-slice --phase <P> --slice <P>.F<n> --name "..." --kind fix`) and leave the review slice open for re-review; do not finish or archive.
- On `blocked`: record the blocker; do not finish or archive.

Stop after one slice. Do not advance to the next slice in the same turn.
