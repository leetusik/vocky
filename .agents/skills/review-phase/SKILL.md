---
name: review-phase
description: Review a completed phase against its objective and record a pass / changes_requested / blocked verdict.
---

# review-phase

The phase review is executed by `slice-executor-high` — the top executor tier; reviews never run on a lower tier — dispatched by the orchestrator at the `REVIEW` slice; this is its checklist. It is where the phase's slices are **validated together** — the orchestrator trusted each executor's `done` and did not re-run per-slice validation, so re-run it here across the whole phase — and where the phase's durable-doc changes are **consolidated into new versions on a passing review** (from the "Doc impact" notes in `phase.md`). Write only docs here, never source code; do not implement fixes — those are done by fix slices.

Read:

- `AGENTS.md` (or `CLAUDE.md`)
- `docs/current/*.md` relevant to the phase, and `docs/index.json`
- `works/state.json`, `works/backlog.md`
- the phase folder under `works/phases/active/<P>/` and each completed slice's `slice.json` + `result.md`

Check:

- Did the phase objective actually ship?
- Did each slice meet its brief and plan? Are deviations explained in `result.md`?
- **Validate all slices together** (the orchestrator no longer re-runs per-slice validation): re-run each slice's validation commands from its `plan.md` / `result.md`, plus `python3 scripts/workflow.py validate`. Do they pass across the finished phase?
- Were the phase's durable-truth changes (product, architecture, API, …) consolidated into new doc versions **at this review** — not per-slice, not in-place edits?
- Do `docs/current/*.md` match the latest versions in `docs/index.json` after consolidation? (`python3 scripts/workflow.py validate` checks this.)
- Are any issues serious enough to require fix slices?

On a **passing** review, before recording `pass`, consolidate docs: for each durable-truth area changed across the phase (per the "Doc impact" notes in `phase.md`), run `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source <P>.REVIEW`, edit only the returned `edit_path`, then `python3 scripts/workflow.py rebuild-docs` — one version per affected doc, capturing the whole phase. On `changes_requested` / `blocked`, version nothing — fixes land first and the eventual passing re-review consolidates them.

The orchestrator records exactly one verdict (the executor returns it; the executor never runs `review-phase` itself):

```sh
python3 scripts/workflow.py review-phase <P> --verdict pass --reviewer slice-executor-high --note "short justification"
# or
python3 scripts/workflow.py review-phase <P> --verdict changes_requested --reviewer slice-executor-high --note "numbered issues + proposed fix slices like P1.F1"
# or
python3 scripts/workflow.py review-phase <P> --verdict blocked --reviewer slice-executor-high --note "the blocker and needed input"
```

`pass` also marks the phase `done` **and closes the `REVIEW` slice** — the phase stays in `active/`; archiving is a separate, manual step (`archive-all`, `rotate-backlog`, or `archive-phase`). `changes_requested` returns the phase to `in_progress` and sets the `REVIEW` slice to `changes_requested` (reopened for re-review). `blocked` sets **both the phase and the `REVIEW` slice** `blocked`.
