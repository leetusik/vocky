# Plan

- Work item: works/current/20260424_1644_decompose_admin_rest_api
- Created at: 20260424_1644
- Phase ID: P3
- Phase: Admin REST API for human review
- Slice ID: P3.DECOMP
- Slice: decompose phase

## Context

P1/P2 implemented MCP surfaces for AI workflows. P3 adds a separate human/operator REST API over the same feedback schema.

## Goal

Lock P3 details before implementation starts.

## Scope

- In scope: Decide P3 route namespace, auth default, query endpoints, management endpoints, and docs scope.
- Out of scope: Implementing code in this decompose slice.

## Approach

Use Starlette routes under `/admin/api`. Add optional bearer-token protection for `/admin/api/*` using a new admin token setting. Implement list/detail query endpoints for all records, then patch/delete management endpoints. Keep MCP and Admin route handlers separate while sharing service/repository/database layers.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1644_decompose_admin_rest_api/plan.md`
- `works/current/20260424_1644_decompose_admin_rest_api/result.md`

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Admin API should not be exposed publicly without bearer protection.
- Starlette is already the host framework, so no new FastAPI dependency is needed for this phase.

## Verification Plan

- Manual backlog review.

## Planned Commits

- Not committing unless requested.
