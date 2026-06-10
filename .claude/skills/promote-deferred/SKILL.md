---
name: promote-deferred
description: Promote a deferred job into an active phase or slice.
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# promote-deferred

Run `python3 scripts/workflow.py promote-deferred $ARGUMENTS` (for example `D1 --phase P1 --slice P1.S2 --name "..."`; add `--create-phase --phase-name "..." --phase-objective "..."` to start a new phase).

This moves the job from `works/deferred/open/` to `works/deferred/promoted/`, creates a slice folder, and carries the deferred context into the slice brief.
