---
description: Continue the current backlog phase one slice at a time (backlog-driven).
---

Read CLAUDE.md, works/backlog.md, works/deferred.md, and any in-progress folders under works/current/. Follow the "Execution Commands" rules in CLAUDE.md.

Resolve the current phase: scan works/backlog.md top-to-bottom and pick the first phase whose status is not `done`. If that phase is `blocked`, surface the blocker and stop.

Resolve the next slice: the first slice in the current phase whose status is not `done`. Do not skip fix slices or `phase review` slices.

If the next slice is `phase review`, invoke the `phase-reviewer` subagent (Agent tool, subagent_type: phase-reviewer) and apply its verdict per CLAUDE.md.

Otherwise: if a matching active work item already exists under works/current/, continue it. If not, run `scripts/start_work.sh <phase_id> <slice_id> <slug>` to create one. Fill plan.md before code changes, implement, then fill result.md.

Stop after one slice. Do not advance to the next slice in the same turn.
