# Plan

- Work item: works/current/20260424_1505_review_generalize_public_access_docs
- Created at: 20260424_1505
- Phase ID: P1
- Phase: Generalize public access docs
- Slice ID: P1.REVIEW
- Slice: phase review

## Context

The cleanup slice generalized tracked public-access docs/artifacts and created an ignored local note for concrete deployment values.

## Goal

Verify tracked files no longer contain personal domain or registrar details and that the focused tests still pass.

## Scope

- In scope:
  - Search non-ignored repo files for personal values.
  - Confirm the local note is ignored.
  - Run focused public access tests.
  - Close the phase if review passes.
- Out of scope:
  - Changing public access runtime behavior.

## Approach

Use `rg` with normal ignore behavior to validate tracked/unignored content, `git status --ignored` for the local note, and pytest for focused behavior.

## Affected Files

- `works/backlog.md`
- Review work item files

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `.env.example`

## Risks and Open Questions

- The ignored local note intentionally contains the concrete values and should only appear when using `--no-ignore`.

## Verification Plan

- Search non-ignored repo files for the concrete local domain, Tailscale host, and registrar name.
- Search the ignored local note with `--no-ignore` to confirm it contains the concrete local setup.
- `git status --short --ignored docs/local-public-access.md`
- `uv run pytest tests/test_public_access.py -q`
- `git diff --check`

## Planned Commits

- `docs(public-access): keep custom-domain examples generic`
