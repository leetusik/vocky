# Plan

- Work item: works/current/20260427_1244_review_in_app_operator_documentation
- Created at: 20260427_1244
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.REVIEW
- Slice: phase review

## Goal

Verify P2 end to end and close the phase only if the in-app operator documentation is correctly packaged, routed, tested, and aligned with durable docs.

## Scope

- Review Admin UI route/auth boundaries and confirm `/admin/assets/docs.json` is static and unauthenticated like CSS/JS.
- Verify packaged asset behavior, including a wheel contents check for `index.html`, `app.css`, `app.js`, and `docs.json`.
- Check docs content coverage against P2 objectives and durable docs, including API/auth, self-hosting, and public custom-domain guidance.
- Check responsive Docs UI structure and scan content for SaaS tenant/account/billing concepts.
- Run focused tests and attempt the full suite; record any environment blocker.

## Context

- P2.S1, P2.S2, and P2.S3 are done and archived.
- No public API or storage contracts should have changed in this phase.
- If review finds blocking issues, create fix slices before marking P2 done.

## Milestones

1. Inspect code/content/durable docs for review risks.
2. Build a wheel and confirm Admin assets are packaged.
3. Run focused and full verification, then decide pass/fix.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`
- `uv build --wheel`
- Wheel contents check for Admin assets
- `uv run pytest`

## Risks / open questions

- Full-suite verification may require local PostgreSQL/Redis test services; record explicit blockers if unavailable.

## Docs to update

- None planned unless review finds a mismatch.
