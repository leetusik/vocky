# Plan

- Work item: works/current/20260427_1436_decompose_self_hosted_packaging_polish
- Created at: 20260427_1436
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.DECOMP
- Slice: decompose phase

## Goal

Break P5 into concrete, ordered implementation slices that make the Admin Web UI reliable for self-hosted local/Compose workflows, packaged runtime behavior, public custom-domain access, documentation, tests, and release-facing README messaging.

## Scope

- Update `works/backlog.md` only for P5 scheduling.
- Add middle slices before `P5.REVIEW`.
- Mark this decomposition slice complete after the backlog is decision-ready for implementation.
- Do not change app code, tests, README, or durable docs in this slice.

## Context

- P5 currently contains only `P5.DECOMP` and `P5.REVIEW`.
- Earlier phases implemented the Admin Web UI shell, in-app docs, dashboard metrics, and feedback review/manage workflows.
- P5 should preserve the self-hosted default model while hardening packaging, local verification, public custom-domain guidance, and release polish.

## Milestones

1. Add focused middle slices for Compose/local workflow hardening, packaged Admin UI asset verification, public custom-domain/external access polish, and release-facing docs polish.
2. Keep `P5.REVIEW` last and open as the phase gate.
3. Mark `P5.DECOMP` done with this work item linked from the backlog.

## Validation

- Inspect `works/backlog.md` after edits and confirm P5 ordering and statuses.
- No pytest run is required because this slice only changes workflow scheduling artifacts.

## Risks / open questions

- Existing uncommitted work outside this slice must be preserved.
- Later P5 slices may discover additional fix slices during phase review.

## Docs to update

- None in this slice. Documentation changes are scheduled for a later P5 implementation slice.
