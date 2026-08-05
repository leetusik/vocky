---
name: review-phase
description: Review a completed phase against its objective and record a pass / changes_requested / blocked verdict.
---

# review-phase

The phase review is executed by `slice-executor-high` — the top executor tier; reviews never run on a lower tier — dispatched by the orchestrator at the `REVIEW` slice; this is its checklist. It is where the phase's slices are **validated together** — the orchestrator trusted each executor's `done` and did not re-run per-slice validation, so re-run it here across the whole phase — and where the phase's durable-doc changes are **consolidated into new versions on a passing review** (from the "Doc impact" notes in `phase.md`). Write only docs here, never source code; do not implement fixes — those are done by fix slices.

**Parallel mode changes exactly one thing: the consolidation.** If the phase's `phase.json` carries an `execution` block with `mode: "parallel"` (the review then runs in that phase's branch worktree), a passing review creates **no** doc versions — doc versions are allocated from one shared `docs/index.json`, so two branches consolidating at once collide. Everything else — validating all slices together, judging the phase, recording the verdict — is unchanged. See the `parallel-phase` skill for the post-merge sequence that consolidates instead.

Read:

- `AGENTS.md` (or `CLAUDE.md`)
- `docs/current/*.md` relevant to the phase, and `docs/index.json`
- `works/state.json`, `works/backlog.md`
- the phase folder under `works/phases/active/<P>/` and each completed slice's `slice.json` + `result.md`

Check:

- Did the phase objective actually ship?
- Did each slice meet its brief and plan? Are deviations explained in `result.md`?
- **Validate all slices together** (the orchestrator no longer re-runs per-slice validation): re-run each slice's validation commands from its `plan.md` / `result.md`, plus `python3 scripts/workflow.py validate`. Do they pass across the finished phase?
- Were the phase's durable-truth changes (product, architecture, API, …) consolidated into new doc versions **at this review** — not per-slice, not in-place edits? (Parallel mode: instead check that the "Doc impact" list in `phase.md` **covers every durable-truth change the phase made** — that list is the sole input to the post-merge consolidation, so an incomplete list is a review finding, not a detail.)
- Do `docs/current/*.md` match the latest versions in `docs/index.json` after consolidation? (`python3 scripts/workflow.py validate` checks this.) In parallel mode this applies at consolidation time on the default stream, not at the branch review.
- Are any issues serious enough to require fix slices?

**Form the verdict from the complete picture, then branch on it.** Finish the validation and the judgment across every slice *first* — never abort at the first failing check, or the orchestrator learns one finding per review cycle instead of all of them at once. Only once the verdict is settled does the review split:

- On a **passing** review, before recording `pass`, consolidate docs: for each durable-truth area changed across the phase (per the "Doc impact" notes in `phase.md`), run `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source <P>.REVIEW`, edit only the returned `edit_path`, then `python3 scripts/workflow.py rebuild-docs` — one version per affected doc, capturing the whole phase. **In parallel mode, skip this step entirely**: run no `doc-new-version` and no `rebuild-docs` on the branch, and report `doc_versions: none — deferred to post-merge consolidation (parallel mode)`. The orchestrator consolidates on the default stream after the merge, from the same "Doc impact" list you just verified (`parallel-phase` skill).
- On **`changes_requested` or `blocked`, stop here and hand back.** Doc consolidation is pass-only work: do not run it, and do no other pass-only step either. Return to the orchestrator the verdict, the numbered findings, and the proposed fix slices (`<P>.F<n>`, one line of scope each); it decides what happens next — create the fix slices, or take the decision to the operator. This is a full stop, not a skipped step you carry on past: the review ends there, and the docs stay unversioned until a later passing re-review consolidates the whole phase in one go.

**The review does not write the phase explainer.** Explaining is a separate operation the operator runs when they want one (`/explain`); it left the review's default behaviour, so the review locates no explain skill, runs no KB probe, and has no offline fallback or commit of any kind. Its whole obligation is one pointer line, reported in `result.md` and in the structured return, identical on every verdict: `explain: not written — run /explain for this phase`.

The orchestrator records exactly one verdict (the executor returns it; the executor never runs `review-phase` itself):

```sh
python3 scripts/workflow.py review-phase <P> --verdict pass --reviewer slice-executor-high --note "short justification"
# or
python3 scripts/workflow.py review-phase <P> --verdict changes_requested --reviewer slice-executor-high --note "numbered issues + proposed fix slices like P1.F1"
# or
python3 scripts/workflow.py review-phase <P> --verdict blocked --reviewer slice-executor-high --note "the blocker and needed input"
```

`pass` also marks the phase `done` **and closes the `REVIEW` slice** — the phase stays in `active/`; archiving is a separate, manual step (`archive-all`, `rotate-backlog`, or `archive-phase`). `changes_requested` returns the phase to `in_progress` and sets the `REVIEW` slice to `changes_requested` (reopened for re-review). `blocked` sets **both the phase and the `REVIEW` slice** `blocked`. For a parallel-mode phase, a recorded `pass` is also what opens the integration sequence the orchestrator then runs (`parallel-gate <P>` → push → PR → CI → merge → `parallel-merge-finish` → deferred consolidation → `parallel-consolidated <P>` → `parallel-teardown <P>`); archiving stays blocked until that consolidation is recorded.
