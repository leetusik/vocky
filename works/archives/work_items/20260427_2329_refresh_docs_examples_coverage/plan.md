# Plan

- Work item: works/current/20260427_2329_refresh_docs_examples_coverage
- Created at: 20260427_2329
- Phase ID: P4
- Phase: Working REST capture Try docs
- Slice ID: P4.S3
- Slice: refresh docs examples and coverage

## Goal

Package the REST capture try-it block in Admin docs and cover it in asset and package validation.

## Scope

- Update `src/vocky/admin_assets/docs.json` to include a `rest_capture_try` block in the REST Capture topic.
- Seed the default payload with website/product-surface feedback and the text `피드백을 보내주세요!` in `message` and `target_text`.
- Update Admin UI route/asset tests and package-check expectations for the renderer, CSS, storage key, docs block, and default payload.

## Context

- `P4.S2` added renderer support but did not activate it in packaged docs.
- The docs block is an internal packaged-docs shape, not a backend API contract.
- Existing tests assert direct asset contents and package-check verifies built wheel contents.

## Milestones

1. Add the REST capture try-it block to `docs.json`.
2. Update `tests/test_admin_ui.py` expectations.
3. Update `scripts/check_admin_ui_package.py` package expectations.
4. Run JSON, JS, targeted pytest, and package-check validation.

## Validation

- `uv run python -m json.tool src/vocky/admin_assets/docs.json >/dev/null`
- `node --check src/vocky/admin_assets/app.js`
- `uv run pytest tests/test_admin_ui.py tests/test_capture_api.py tests/test_public_access.py`
- `make package-check`

## Risks / open questions

- Keep the default payload valid for the existing REST capture schema.
- Ensure the docs still explain the real queued-feedback side effect and separate API token.

## Docs to update

- `src/vocky/admin_assets/docs.json`
