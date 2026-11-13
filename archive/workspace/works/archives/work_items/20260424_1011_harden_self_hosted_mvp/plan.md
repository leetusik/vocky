# Plan

- Work item: works/current/20260424_1011_harden_self_hosted_mvp
- Created at: 20260424_1011
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.DECOMP
- Slice: decompose phase

## Context

- `P4` is the first phase in `works/backlog.md` whose status is not `done`, so it is the active execution target.
- The previous phases implemented the MCP capture and review/query surfaces, but the local operator story is still rough: the `Makefile` depends on ad hoc env overrides, the README shows non-default ports as the main path, and the phase is not yet decomposed into concrete hardening slices.
- This phase must stay Compose-first for self-hosted users and must not change MCP contracts or add automatic migrations on app startup.

## Goal

Break `P4` into concrete, reviewable slices for operator workflow alignment, durable documentation, fresh-install verification, and final phase review.

## Scope

- In scope:
- Update `works/backlog.md` so `P4` contains `P4.S1`, `P4.S2`, `P4.S3`, and `P4.REVIEW` with notes aligned to the approved phase plan.
- Move `P4` from `planned` into active execution and bind `P4.DECOMP` to this work item.
- Record the decomposition outcome in this work item.
- Out of scope:
- Implementing the Makefile, README, or verification changes themselves.
- Any MCP contract, database schema, or app-startup migration behavior changes.

## Approach

Use the approved phase plan as the source of truth, update the backlog so the phase has explicit workflow-alignment, runbook, verification, and review slices, and leave `P4.REVIEW` open until the later review pass decides whether fix slices are needed.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1011_harden_self_hosted_mvp/plan.md`
- `works/current/20260424_1011_harden_self_hosted_mvp/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The decomposition needs to preserve the mandatory `P4.DECOMP` and `P4.REVIEW` slices while adding only the middle slices that materially support the self-hosted hardening objective.
- The slice notes need to make the Compose-first intent explicit so later implementation work does not drift toward direct-process workflows.

## Verification Plan

- Re-read the updated `P4` section in `works/backlog.md` to confirm the phase status, work-item link, and slice ordering match the approved plan.

## Planned Commits

- None.
