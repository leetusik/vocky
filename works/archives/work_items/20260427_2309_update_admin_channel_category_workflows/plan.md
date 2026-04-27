# Plan

- Work item: works/current/20260427_2309_update_admin_channel_category_workflows
- Created at: 20260427_2309
- Phase ID: P3
- Phase: Channel categories and Admin adjustability
- Slice ID: P3.S3
- Slice: update Admin channel category workflows

## Goal

Replace free-text Admin Web UI channel controls with category-aware nullable controls while preserving legacy stored channel display and same-origin Admin REST behavior.

## Scope

- Replace the feedback list channel filter text input with an `Any`/`web`/`mobile`/`support` select.
- Replace the feedback edit channel input with a nullable category select.
- Preserve stored legacy channel display in list and detail views.
- In edit mode, include a selected `Legacy: <value>` option for legacy records and omit `channel` from PATCH unless the operator picks `None` or an allowed category.
- Keep layout and API routing unchanged.

## Context

- `P3.S2` now rejects arbitrary non-null channel writes from Admin REST while leaving legacy records readable.
- The UI must avoid sending legacy arbitrary values back during save when the operator did not intentionally change channel.
- Admin REST query filters remain exact-match and can still filter legacy values outside the UI.

## Milestones

1. Inspect Admin HTML/JS tests and current channel controls.
2. Update filter markup and request-building logic for category select behavior.
3. Update detail edit rendering and PATCH payload logic for nullable, allowed, and legacy-preserve states.
4. Add focused Admin UI tests for filter select and edit select behavior.
5. Run targeted Admin UI tests.

## Validation

- `uv run pytest tests/test_admin_ui.py -q`

## Risks / open questions

- Legacy-preserve behavior must be explicit in the client state so a selected legacy option does not send an invalid Admin REST patch.

## Docs to update

- None planned for this slice; P3.S4 owns documentation and packaged docs copy.
