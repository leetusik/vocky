# Plan

- Work item: works/current/20260424_1303_decompose_generic_self_host_access_phase
- Created at: 20260424_1303
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

- The active backlog is still the template placeholder, but the user provided a concrete `P1` implementation plan for generic self-hosted access and env-driven networking.
- The current self-hosted workflow already uses `.env`, Compose, and Make, but host publishing is still tied only to ports and the docs do not yet define an external-access surface for optional Tailscale usage.
- `AGENTS.md` requires the phase to be explicitly decomposed in `works/backlog.md` before implementation proceeds.

## Goal

Turn the placeholder `P1` backlog entry into the concrete generic self-host access phase, define the ordered slices from the provided plan, and start the phase under tracked work-item execution.

## Scope

- In scope:
- Replace the template `P1` phase metadata in `works/backlog.md` with the real objective, slice list, and work-item linkage.
- Mark `P1.DECOMP` as the active slice and keep the phase open for the remaining implementation and review slices.
- Record the decomposition result in this work item.
- Out of scope:
- Implementation of the env, Compose, Make, or documentation changes themselves.
- Phase review or any fix slices.

## Approach

Use the provided plan as the authoritative phase design, update the backlog to reflect that design, and capture the chosen phase objective and slice ordering in the work-item artifacts.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1303_decompose_generic_self_host_access_phase/plan.md`
- `works/current/20260424_1303_decompose_generic_self_host_access_phase/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The phase naming and slice scope need to stay aligned with the user-provided plan so later slices do not drift.
- The repo already has unrelated dirty changes, so this slice should only touch workflow artifacts.

## Verification Plan

- Re-read the updated `works/backlog.md` and confirm it contains the requested `P1` objective, the mandatory review slices, and the four middle slices from the provided plan.

## Planned Commits

- None.
