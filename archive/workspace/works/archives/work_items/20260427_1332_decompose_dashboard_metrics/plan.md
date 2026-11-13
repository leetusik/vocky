# Plan

- Work item: works/current/20260427_1332_decompose_dashboard_metrics
- Created at: 20260427_1332
- Phase ID: P3
- Phase: Dashboard metrics
- Slice ID: P3.DECOMP
- Slice: decompose phase

## Goal

Break `P3` into concrete, ordered dashboard metrics slices so future work can implement the phase without deciding scope or sequencing during execution.

## Scope

- Update `works/backlog.md` for `P3` only.
- Mark `P3.DECOMP` complete and link this work item.
- Add middle implementation slices before `P3.REVIEW`.
- Do not change application code, tests, reference docs, or UI assets in this slice.

## Context

- `P3` currently has only mandatory `decompose phase` and `phase review` slices.
- The Admin REST surface already has protected feedback list/detail/patch/delete routes.
- The Admin Web UI dashboard currently shows Admin API health and placeholder runtime/auth cards.
- Dashboard metrics need counts, trend data, recent activity, and filterable time windows; a minimal Admin REST metrics endpoint is expected to be the clean backing contract.

## Milestones

1. Add the `P3.DECOMP` work item to the phase and move the phase into progress.
2. Define the future Admin dashboard metrics API slice.
3. Define the future dashboard data/time-window UI slice.
4. Define the future dashboard rendering/recent-activity slice.
5. Leave `P3.REVIEW` open after the new slices.

## Validation

- Inspect `works/backlog.md` and confirm `P3` slice order is `P3.DECOMP`, `P3.S1`, `P3.S2`, `P3.S3`, `P3.REVIEW`.
- Confirm every new slice has a stable ID, checkbox, status, work item field, and actionable notes.
- Confirm no application code or reference docs were changed by this slice.

## Risks / open questions

- Future `P3.S1` should validate whether the metrics endpoint can reuse existing service/repository summary logic cleanly or needs a small dashboard-specific aggregate type.
- Keep the future endpoint under `/admin/api/*` so existing Admin bearer-token middleware protects it.

## Docs to update

- None in this decomposition slice.
- Future `P3.S1` should update `docs/api.md` and `docs/architecture.md` when the Admin metrics endpoint contract is implemented.
