# Plan

- Work item: works/current/20260424_1728_audit_admin_rest_contracts
- Created at: 20260424_1728
- Phase ID: P1
- Phase: Review fast-built feedback MCP/Admin backlog
- Slice ID: P1.S3
- Slice: audit Admin REST contracts

## Context

P1 reviews the feedback MCP/Admin work that was built quickly before this review phase. P1.S3 focuses on the human/operator Admin REST surface under `/admin/api/*` and checks the implementation, tests, README, and durable docs for consistency.

## Goal

Validate that Admin REST routing, optional bearer auth, list/detail/patch/delete behavior, shared service usage, error mapping, and documentation match the documented Admin REST contract. Identify required corrections as explicit follow-up fix slices rather than making unrelated changes inside the audit.

## Scope

- In scope:
  - Admin REST handlers and routes in `src/vocky/admin_api.py`.
  - Shared auth middleware and app route ordering relevant to `/admin/api/*`.
  - Feedback service/repository methods used by Admin REST detail, update, delete, and list endpoints.
  - Tests covering Admin REST behavior and public Admin auth/access behavior.
  - Admin REST sections in `README.md`, `docs/api.md`, and `docs/architecture.md`.
  - Backlog/work-item updates for this audit slice.
- Out of scope:
  - MCP-specific tool behavior already covered by P1.S2.
  - New dashboard UI behavior.
  - Optional Admin enhancements beyond required contract corrections.

## Approach

1. Inspect Admin REST routing, request parsing, validation, serialization, update normalization, and error handling.
2. Inspect auth middleware and route ordering where it affects `/admin/api/*`.
3. Compare behavior with `docs/api.md`, `docs/architecture.md`, README Admin REST text, and test expectations.
4. Run focused Admin REST tests.
5. Record findings in `result.md`, update `works/backlog.md`, and add fix slices only for required corrections.

## Affected Files

- `src/vocky/admin_api.py`
- `src/vocky/auth.py`
- `src/vocky/app.py`
- `src/vocky/feedback/service.py`
- `src/vocky/feedback/repository.py`
- `tests/test_admin_api.py`
- `tests/test_public_access.py`
- `README.md`
- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1728_audit_admin_rest_contracts/plan.md`
- `works/current/20260424_1728_audit_admin_rest_contracts/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`

## Risks and Open Questions

- Admin PATCH semantics can drift from the documented mutable fields; compare allowed updates directly.
- Admin REST shares the service/repository layer with MCP, so only Admin-specific contract gaps should produce fix slices here.
- Public deployments rely on operator-set `VOCKY_ADMIN_AUTH_TOKEN`; confirm docs and middleware align.

## Verification Plan

- Inspect Admin REST source, tests, and docs.
- Run `uv run pytest tests/test_admin_api.py tests/test_public_access.py -q`.
- Record whether P1.F2+ slices are needed.

## Planned Commits

- None planned for this audit slice unless the user later asks for a commit.
