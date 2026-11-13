# Plan

- Work item: works/current/20260424_1646_add_admin_feedback_query_endpoints
- Created at: 20260424_1646
- Phase ID: P3
- Phase: Admin REST API for human review
- Slice ID: P3.S2
- Slice: add admin feedback query endpoints

## Context

P3.S1 added the Admin REST namespace. Human operators now need list/detail endpoints that can inspect all feedback data, including likes, dislikes, comments, metadata, and full contexts.

## Goal

Add Admin REST query endpoints over the shared feedback service and repository.

## Scope

- In scope: `GET /admin/api/feedback`, `GET /admin/api/feedback/{id}`, query filtering, serialization, service/repository get support, and tests.
- Out of scope: Patch/delete management operations and docs.

## Approach

Reuse `FeedbackService.list_feedback` for list queries and add a service/repository get-by-id method for detail. Keep Admin JSON responses separate from MCP tool handlers.

## Affected Files

- `src/vocky/admin_api.py`
- `src/vocky/feedback/repository.py`
- `src/vocky/feedback/service.py`
- `tests/test_admin_api.py`

## Reference Docs To Review

- `docs/api.md`

## Risks and Open Questions

- Admin list must not filter to likes by default; it must return all feedback unless filters are supplied.

## Verification Plan

- Add tests for list filters across likes/dislikes and detail lookup.
- Run Admin API and persistence tests.

## Planned Commits

- Not committing unless requested.
