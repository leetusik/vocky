# Plan

- Work item: works/current/20260424_1502_decompose_generalize_public_access_docs
- Created at: 20260424_1502
- Phase ID: P1
- Phase: Generalize public access docs
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

The public access phase put the user's concrete domain into tracked docs and archived work artifacts. The user wants tracked docs to stay general and the personal setup to live in a gitignored markdown file.

## Goal

Decompose this cleanup into a single implementation slice plus review.

## Scope

- In scope:
  - Generalize tracked README/reference docs/examples/tests/work artifacts.
  - Add a gitignored local markdown file for the user's concrete domain setup.
- Out of scope:
  - Reverting public access functionality.

## Approach

Run one cleanup slice, then review with repository-wide searches for the personal domain and focused tests.

## Affected Files

- `works/backlog.md`
- Work item plan/result files

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Archived work items from the previous phase are new untracked files and need to be sanitized before they are committed.

## Verification Plan

- Search tracked/untracked repo content for the personal domain.
- Run focused public access tests.

## Planned Commits

- `docs(public-access): keep custom-domain examples generic`
