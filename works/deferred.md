# Deferred Jobs

## Purpose

- Track work that is intentionally postponed outside the active execution order in `works/backlog.md`.
- Keep `works/backlog.md` focused on phases and slices that should drive `do the next slice` and `do the whole phase`.
- Promote deferred jobs back into `works/backlog.md` when they are ready to be scheduled.

## Usage Guide

- If the user asks to save tasks, follow-ups, later work, or ideas to `works/deferred.md`, add entries here immediately.
- A direct save-to-deferred request does not need a backlog phase, slice, or work-item folder.
- During slice implementation, add a deferred job when meaningful later work is discovered and it is not appropriate to add it to the current backlog as a slice, fix slice, or phase.
- Do not use this file for work required to complete the current slice or for issues required to make the current phase pass review. Those belong in the active work item or in review-driven fix slices.
- Deferred jobs do not affect current-phase selection. They become scheduled only after being promoted into `works/backlog.md`.

## Entry Rules

- Use stable deferred IDs such as `D1`, `D2`, or `D3`.
- Each deferred job should include a title, status, source, reason, and trigger for re-entry.
- Keep deferred jobs out of `works/backlog.md` until you actually want them to participate in active execution ordering.
- To add a job, scan existing `D*` entries and use the next unused number.
- Keep entries concise, actionable, and traceable to their source.
- If the source is a user request, write `Source: user request`.
- If the source is implementation work, write the phase/slice ID or work-item path when available.
- If the trigger is unknown, use `Trigger: user promotes or schedules this job`.

## Status Model

- `deferred`
- `ready`
- `done`
- `dropped`

## Deferred Jobs

### D1: Refine trajectory-aware feedback export model

- Deferred ID: `D1`
- Status: deferred
- Source: user request
- Reason: The idea is important product direction but is not yet decomposed into an active backlog phase or implementation slice.
- Trigger: user promotes or schedules this job
- Notes:
  - Raw concern captured in `works/later_concerns.md` as `C1`.
  - Refine the concern into product, architecture, API, and export-schema backlog work before implementation.

## Entry Template

```md
### D<N>: <title>

- Deferred ID: `D<N>`
- Status: deferred
- Source: <user request | phase/slice/work item>
- Reason: <why this is parked instead of active backlog work>
- Trigger: <when to promote into works/backlog.md>
- Notes:
  - <optional concise context>
```
