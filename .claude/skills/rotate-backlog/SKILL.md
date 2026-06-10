---
name: rotate-backlog
description: Archive every currently-done phase and leave in-progress phases active (partial archive-all).
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# rotate-backlog

Archive every phase that is **currently done** (all slices complete with a passing review) and leave in-progress phases active, then rebuild the dashboards:

```sh
python3 scripts/workflow.py rotate-backlog
```

This is the **partial** rotation `archive-all` cannot do: `archive-all` refuses unless *every* active phase is done, while `rotate-backlog` sweeps just the done phases and leaves the rest. Use it when several phases are active and only some have passed review.

Archives whole phases only; unfinished, blocked, or unreviewed phases are left untouched. There is no `--force` — to archive an unfinished phase, use `archive-phase <P> --force`.
