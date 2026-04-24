# Plan

- Work item: works/current/20260424_1502_move_personal_domain_notes_out_of_tracked_docs
- Created at: 20260424_1502
- Phase ID: P1
- Phase: Generalize public access docs
- Slice ID: P1.S1
- Slice: move personal domain notes out of tracked docs

## Context

Tracked docs and new work artifacts currently mention the user's concrete domain. The requested state is generic tracked docs plus a gitignored personal note.

## Goal

Keep public access instructions reusable by replacing personal values with generic example domains in tracked files, and place the concrete setup in an ignored markdown file.

## Scope

- In scope:
  - Replace concrete domain references in README, docs, examples, tests, `.env.example`, and work artifacts.
  - Add `.gitignore` coverage for the local markdown note.
  - Create the local markdown note with the concrete domain setup.
- Out of scope:
  - Changing the public access implementation behavior.

## Approach

Use `vocky.example.com` and `example.com` in tracked examples. Add `docs/local-public-access.md` to `.gitignore` and create that file for the user's concrete local setup.

## Affected Files

- `.gitignore`
- `.env.example`
- `README.md`
- `docs/architecture.md`
- `tests/test_public_access.py`
- `works/archives/...`
- `docs/local-public-access.md`

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Need to sanitize archived work artifacts too, because they are part of the generated repo artifacts from the prior phase.

## Verification Plan

- Search for the personal domain after edits.
- Run focused public-access tests.

## Planned Commits

- `docs(public-access): keep custom-domain examples generic`
