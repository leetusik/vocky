# Plan

- Work item: works/current/20260427_1114_decompose_web_ui_foundation
- Created at: 20260427_1114
- Phase ID: P1
- Phase: Self-hosted Web UI foundation
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Decompose P1 into concrete middle slices for the self-hosted Admin Web UI foundation before implementation starts.

## Scope

- In scope: Update `works/backlog.md` with P1 implementation slices, mark `P1.DECOMP` complete, and record this work item.
- Out of scope: Implementing browser routes, static assets, UI code, tests, or reference-doc edits in this slice.

## Context

- Current service is Starlette-only with MCP mounted under `/mcp`, public REST capture under `/api/*`, and Admin REST under `/admin/api/*`.
- `/admin` is currently unused and is the intended browser UI entrypoint.
- Chosen browser auth approach is client-entered `VOCKY_ADMIN_AUTH_TOKEN` stored in session storage and sent as `Authorization: Bearer ...` to `/admin/api/*`.
- Keep P1 focused on the UI foundation; later phases handle in-app documentation, metrics, feedback review, and packaging polish.

## Milestones

1. Add middle slices for docs direction, Admin UI route/static serving, and operator navigation/token client.
2. Mark P1 as `in_progress` and `P1.DECOMP` as `done`.
3. Link this work item in the P1 work-item list and `P1.DECOMP` slice row.

## Validation

- Manual review of `works/backlog.md` confirming the final P1 slice order is `P1.DECOMP`, `P1.S1`, `P1.S2`, `P1.S3`, and `P1.REVIEW`.
- Confirm this slice changes only backlog/work-item files.

## Risks / open questions

- Future route work must preserve `/mcp`, `/api/*`, and `/admin/api/*` behavior.
- Future UI work should not introduce SaaS account, tenant, organization, billing, or managed-cloud auth concepts.

## Docs to update

- None in this slice. `P1.S1` will update `docs/product.md` and `docs/architecture.md`.
