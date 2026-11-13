# Plan

- Work item: works/current/20260424_1648_add_admin_feedback_management_endpoints
- Created at: 20260424_1648
- Phase ID: P3
- Phase: Admin REST API for human review
- Slice ID: P3.S3
- Slice: add admin feedback management endpoints

## Context

P3.S2 added Admin REST query endpoints. Operators also need minimal management operations over the same feedback records.

## Goal

Add Admin REST patch/delete endpoints using the shared feedback service and repository.

## Scope

- In scope: `PATCH /admin/api/feedback/{id}` for review-field updates, `DELETE /admin/api/feedback/{id}`, validation, service/repository update/delete methods, and tests.
- Out of scope: Bulk management, audit logs, RBAC, and dashboard UI.

## Approach

Allow patching `feedback_value`, `comment`, `channel`, `tags`, `source_metadata`, and `attributes`. Keep full conversation/context immutable for now so operator edits do not rewrite captured evidence. Add delete for removing bad/test records.

## Affected Files

- `src/vocky/admin_api.py`
- `src/vocky/feedback/repository.py`
- `src/vocky/feedback/service.py`
- `tests/test_admin_api.py`

## Reference Docs To Review

- `docs/api.md`

## Risks and Open Questions

- No audit trail exists yet; docs should call the management surface early-stage.

## Verification Plan

- Add tests for patch, delete, not-found, and validation behavior.
- Run Admin API and persistence tests.

## Planned Commits

- Not committing unless requested.
