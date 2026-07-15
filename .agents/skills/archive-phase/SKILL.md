---
name: archive-phase
description: Archive review-passed phases: archive-all (full sweep), rotate-backlog (partial), or archive-phase (single).
---

# archive-phase

Archiving is **manual and explicit** — never automatic. A passing review marks a phase `done` but leaves it in `active/`; the **operator** decides when to archive (invoking this skill is that decision — never archive unasked). Archive whole phases only, never individual slices. Three first-class options:

**Archive everything — end-of-batch sweep.** When every active phase is done (the last review slice across all phases is complete), sweep them all to archived at once:

```sh
python3 scripts/workflow.py archive-all
```

`archive-all` refuses unless every active phase is `done` with a passing review.

**Rotate the done phases — partial sweep.** When only some phases are done, archive exactly those and leave the in-progress ones active:

```sh
python3 scripts/workflow.py rotate-backlog
```

**Archive one phase.** Archive a single review-passed phase by id:

```sh
python3 scripts/workflow.py archive-phase <P>
```

All three gate on the same rule: a phase must be `done` with a passing review to archive. Use `--force` (on `archive-all`/`archive-phase`) only for exceptional cleanup of an unfinished phase.
