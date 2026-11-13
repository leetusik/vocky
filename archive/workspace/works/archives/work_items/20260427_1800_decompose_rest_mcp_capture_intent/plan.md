# Plan

- Work item: works/current/20260427_1800_decompose_rest_mcp_capture_intent
- Created at: 20260427_1800
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.DECOMP
- Slice: decompose phase

## Goal

Decompose P2 into concrete implementation slices so REST capture can broaden to general server-to-server website/product feedback while MCP capture remains optimized for agent/message feedback.

## Scope

- Update `works/backlog.md` only.
- Mark P2 as started and close `P2.DECOMP`.
- Add concrete middle slices between `P2.DECOMP` and `P2.REVIEW`.
- Preserve the chosen contract direction: adapt existing `POST /api/feedback` in place, with no new versioned or split REST endpoint in this phase.
- Do not change product docs, architecture docs, API docs, code, tests, migrations, or packaged assets in this decomposition slice.

## Context

- The backlog currently has P1 complete and P2 as the first open phase.
- P2 exists to separate capture intent: REST should support general product feedback while MCP remains agent/message-oriented.
- REST capture remains server-to-server and capture-only.
- Existing accepted REST payloads must continue working.
- Later slices should update durable docs before code changes, then split transport handling and add compatibility coverage.

## Milestones

1. Update P2 status, work-item link, and `P2.DECOMP` completion state.
2. Add a docs/contract slice to lock REST-vs-MCP intent before implementation.
3. Add an implementation slice to separate transport input paths while preserving shared queue/service/persistence behavior.
4. Add a guidance and compatibility-test slice for general REST examples and existing payload coverage.
5. Leave `P2.REVIEW` open as the final phase gate.

## Validation

- Inspect `works/backlog.md` after editing.
- Confirm P2 contains `P2.DECOMP`, `P2.S1`, `P2.S2`, `P2.S3`, and `P2.REVIEW` in that order.
- Confirm `P2.REVIEW` remains `todo`.
- No code tests are required because this slice only changes workflow artifacts.

## Risks / open questions

- Existing workspace changes are from prior work and must not be reverted.
- The compatibility direction is locked to in-place adaptation of `POST /api/feedback`.

## Docs to update

- None in this slice. Durable docs updates are scheduled for `P2.S1`.
