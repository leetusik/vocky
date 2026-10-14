---
name: archive-phase
description: "Archive review-passed phases: archive-all (full sweep), rotate-backlog (partial), or archive-phase (single)."
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# archive-phase

Archiving is **manual and explicit** — never automatic. A passing review marks a phase `done` but leaves it in `active/`; the **operator** decides when to archive (invoking this skill is that decision — never archive unasked). Archive whole phases only, never individual slices. Three first-class options:

**Archive everything — end-of-batch sweep.** When every active phase is done (the last review slice across all phases is complete), sweep them all to archived at once:

```sh
python3 scripts/workflow.py archive-all
```

`archive-all` refuses unless every active phase is `done` with a passing review — and, for any phase still owing its deferred doc consolidation, unless that has landed too.

**Rotate the done phases — partial sweep.** When only some phases are done, archive exactly those and leave the in-progress ones active. The default is one step of a chain (the `/rotate-backlog` skill runs it): it checks the doc debt **first** and archives nothing while any stands; when a phase owes consolidation it prints the docs phase to create (or resumes the live one), the skill creates it on the invocation alone and runs it through `create-phase`'s docs-phase route and `do-whole-phase`, and once the docs phase is `done` the sweep archives every done phase, the docs phase included. When nothing owes, it archives the done phases right away:

```sh
python3 scripts/workflow.py rotate-backlog
```

Add `--archive-only` to skip the chain and keep the plain archive-and-report sweep, which creates and runs nothing: `python3 scripts/workflow.py rotate-backlog --archive-only`.

**Archive one phase.** Archive a single review-passed phase by id:

```sh
python3 scripts/workflow.py archive-phase <P>
```

All three gate on the same rule: a phase must be `done` with a passing review to archive. **A phase owing docs has one more gate:** the engine blocks it while `consolidation` is still `"pending"` (`archive-phase` refuses, `archive-all` lists it, `rotate-backlog` leaves it active, and the default run creates and runs the docs phase that pays it before archiving) — that debt is stamped by a passing review whose phase left "Doc impact" notes, and archiving is exactly what would move those notes out of `active/`. Run the docs phase (`docs-debt` for the worklist, `doc-new-version` per note), then `python3 scripts/workflow.py docs-consolidated <P>`; a phase the operator ran in its own worktree merges first and uses `parallel-consolidated <P>` (see the `parallel-phase` skill). Use `--force` (on `archive-all`/`archive-phase`) only for exceptional cleanup of an unfinished phase.
