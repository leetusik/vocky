# Plan

- Work item: works/current/20260425_0041_decompose_web_capture_rest_api
- Created at: 20260425_0041
- Phase ID: P1
- Phase: Public Web Capture REST API
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Decompose `P1` into concrete implementation slices for the public web capture REST API without implementing the REST API in this slice.

## Scope

- Mark `P1` and `P1.DECOMP` as active while decomposition is in progress.
- Add the middle slices needed before `P1.REVIEW`.
- Record the decomposition result and archive this work item.
- Do not change source code, tests, config files, or reference docs in this slice.

## Context

`P1` adds a server-to-server REST capture path for web and product integrations. The phase should reuse the existing MCP capture validation, Redis queue, worker, feedback service, and PostgreSQL storage, while keeping public review/query/summary APIs out of scope.

## Milestones

1. Update `works/backlog.md` to show `P1.DECOMP` in progress.
2. Insert `P1.S1`, `P1.S2`, and `P1.S3` before `P1.REVIEW` with clear slice intent.
3. Mark `P1.DECOMP` done, record the result, and archive the completed work item.

## Validation

- Review `works/backlog.md` manually.
- Confirm `P1` contains `P1.DECOMP`, `P1.S1`, `P1.S2`, `P1.S3`, and `P1.REVIEW` in that order.
- Confirm only backlog/work-item execution artifacts changed.

## Risks / open questions

- The existing uncommitted `works/backlog.md` change is treated as intentional and preserved.
- Implementation starts later with `P1.S1`, not inside `P1.DECOMP`.

## Docs to update

- None for this decomposition slice. `P1.S3` will handle reference and product-facing documentation updates.
