# Plan

- Work item: works/current/20260427_1448_verify_packaged_admin_web_ui_assets
- Created at: 20260427_1448
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S2
- Slice: verify packaged Admin Web UI assets

## Goal

Add an explicit package verification command that builds a wheel and confirms the Admin Web UI assets needed by `/admin` and `/admin/assets/*` are present and structurally valid.

## Scope

- Add a package asset check script or equivalent Make target.
- Add `make package-check`.
- Include packaged asset verification in `make verify`.
- Preserve current unauthenticated `/admin` and `/admin/assets/*` behavior and protected `/admin/api/*` behavior.

## Context

- The Admin UI is served from package resources through `importlib.resources`.
- Existing tests cover local route behavior, but `make verify` does not currently prove the wheel contains `index.html`, `app.css`, `app.js`, and `docs.json`.
- P5.S2 should not change public API contracts.

## Milestones

1. Add a deterministic wheel asset checker for the Admin UI bundle.
2. Add `package-check` and wire it into `verify`.
3. Run focused Admin UI/public-access tests and package verification.

## Validation

- `make package-check`
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py`

## Risks / open questions

- Wheel checks must build into a temporary directory and avoid relying on the existing `dist/` artifact.
- Keep the check lightweight enough to run as part of `make verify`.

## Docs to update

- None planned for this slice.
