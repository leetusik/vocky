# Plan

- Work item: works/current/20260429_1628_implement-identity-trigger-support
- Created at: 20260429_1628
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.S3
- Slice: implement identity and trigger support

## Goal

Implement the accepted `user_id` and trigger fields across capture validation, queueing, service/persistence, read filters, MCP/Admin responses, Admin UI visibility, migration, and focused tests.

## Scope

- Add database columns and indexes for `user_id`, `trigger_type`, `trigger_message`, and `trigger_metadata`.
- Thread fields through MCP and REST capture inputs, normalization, queue serialization/deserialization, service dataclasses, ORM model, repository create/read/filter mapping, response serializers, and Admin UI list/detail surfaces.
- Add exact `user_id` and `trigger_type` filters to MCP read tools and Admin feedback listing while keeping Admin metrics ingest-window-only.
- Preserve capture success response shapes.
- Update durable docs from accepted/planned to implemented once code support lands.

## Context

- P1.S2 defined the contract and allowed trigger values: `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`.
- Optional strings should be trimmed with blank values normalized to `null`.
- `trigger_metadata` must be a JSON object and default to `{}`.
- `trigger_message` and `trigger_metadata` are response-only inspection fields, not read filters.

## Milestones

1. Inspect existing capture/read/queue/persistence/Admin UI/test paths.
2. Add migration/model/repository/service support for the new fields and filters.
3. Update MCP, REST, Admin REST, and Admin UI surfaces.
4. Add focused tests for validation, queue defaults, persistence/filtering, response shape, and UI/docs strings.
5. Run focused verification and record any broader test blockers.

## Validation

- Focused `uv run pytest` targets covering modified validation/API/queue/persistence/Admin/MCP paths.
- `git diff --check`.

## Risks / open questions

- Full database-backed tests may require local PostgreSQL via `TEST_DATABASE_URL`; if unavailable, record the blocker and run non-DB checks that still apply.
- Existing uncommitted P1 docs/backlog work is part of this active phase; `works/later_concerns.md` has unrelated user-owned changes and should remain untouched.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
