---
description: Archive the active backlog and replace it with the fresh template (run only when every phase and slice is done).
allowed-tools: Bash(scripts/rotate_backlog.sh:*)
---

Verify works/backlog.md shows every phase as `done` and every slice as `done`, then run `scripts/rotate_backlog.sh`. Report both the archive path and the new backlog path.
