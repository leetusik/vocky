# Plan

- Work item: works/current/20260424_1642_write_gitignored_changple5_apply_handoff
- Created at: 20260424_1642
- Phase ID: P2
- Phase: Liked conversation retrieval and integration handoff
- Slice ID: P2.S3
- Slice: write gitignored Changple5 apply handoff

## Context

The public guide is tracked and generic. The user also requested a Changple5-specific handoff for other agents, but it should be gitignored and Vocky code should not touch the Changple5 app.

## Goal

Create a local Changple5 apply handoff document and ignore it from tracked docs.

## Scope

- In scope: Update `docs/.gitignore` and add `docs/changple5-apply.md` with concrete integration guidance.
- Out of scope: Editing Changple5 code or adding Changple-specific content to public README/reference docs.

## Approach

Add a gitignore entry for the handoff doc and write instructions for Changple5 agents: MCP endpoint config, explicit action triggers, payload mapping, liked few-shot retrieval, and boundaries.

## Affected Files

- `docs/.gitignore`
- `docs/changple5-apply.md`

## Reference Docs To Review

- `docs/action-feedback-integration.md`

## Risks and Open Questions

- The handoff doc should remain local/ignored; public docs must stay generic.

## Verification Plan

- Confirm `git status --short --ignored docs/changple5-apply.md` reports the handoff as ignored.

## Planned Commits

- Not committing unless requested.
