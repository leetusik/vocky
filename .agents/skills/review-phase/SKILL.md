---
name: review-phase
description: Review a completed phase against its objective and record a pass / changes_requested / blocked verdict.
---

# review-phase

Review the target phase read-only, then record the verdict. Do not implement fixes here; that is done by fix slices.

Read:

- `AGENTS.md` (or `CLAUDE.md`)
- `docs/current/*.md` relevant to the phase, and `docs/index.json`
- `works/state.json`, `works/backlog.md`
- the phase folder under `works/phases/active/<P>/` and each completed slice's `slice.json` + `result.md`

Check:

- Did the phase objective actually ship?
- Did each slice meet its brief and plan? Are deviations explained in `result.md`?
- When product, architecture, or API truth changed, were new doc versions created (not in-place edits)?
- Do `docs/current/*.md` match the latest versions in `docs/index.json`? (`python3 scripts/workflow.py validate` checks this.)
- Were validation commands recorded?
- Are any issues serious enough to require fix slices?

Record exactly one verdict:

```sh
python3 scripts/workflow.py review-phase <P> --verdict pass --reviewer phase-reviewer --note "short justification"
# or
python3 scripts/workflow.py review-phase <P> --verdict changes_requested --reviewer phase-reviewer --note "numbered issues + proposed fix slices like P1.F1"
# or
python3 scripts/workflow.py review-phase <P> --verdict blocked --reviewer phase-reviewer --note "the blocker and needed input"
```

`pass` also marks the phase `done` — it stays in `active/`; archiving is a separate, manual step (`archive-all`, `rotate-backlog`, or `archive-phase`). `changes_requested` returns it to `in_progress`. `blocked` sets it `blocked`.
