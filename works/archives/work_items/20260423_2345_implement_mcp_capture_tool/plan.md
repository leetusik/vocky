# Plan

- Work item: works/current/20260423_2345_implement_mcp_capture_tool
- Created at: 20260423_2345
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.S4
- Slice: implement MCP capture tool

## Context

- `P2.S3` completed the database model, migration, and transport-neutral feedback write service.
- `P2.S4` adds the public MCP tool surface on top of that service, including normalization, validation, and error handling.
- The tool implementation work began immediately after `P2.S3` in the same execution pass; this work item records the intended scope and results for that slice.

## Goal

Implement the `capture_feedback` MCP tool so validated feedback payloads are normalized, persisted, and returned with predictable success and error behavior.

## Scope

- In scope:
  - Add the `capture_feedback` tool with the locked request and response shape.
  - Implement blank-field, timestamp, tag, and optional-field normalization.
  - Map validation and storage failures to MCP tool execution errors.
  - Keep unknown-tool failures as MCP protocol errors.
  - Verify the tool through live MCP calls and record the results.
- Out of scope:
  - The larger pytest suite and README/docs updates for `P2.S5`.
  - Query API work from `P3`.

## Approach

Register the tool on the shared FastMCP server, normalize the raw input into the transport-neutral `CreateFeedbackEvent` payload, catch validation and persistence failures as `CallToolResult(isError=True)`, and replace the default low-level `tools/call` handler so unknown tools remain protocol errors.

## Affected Files

- `src/vocky/mcp_server.py`
- `src/vocky/tools/...`
- `works/backlog.md`
- `works/current/20260423_2345_implement_mcp_capture_tool/plan.md`
- `works/current/20260423_2345_implement_mcp_capture_tool/result.md`

## Reference Docs To Review

- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- FastMCP’s structured-output validation for `CallToolResult` errors is stricter than expected, so the tool needs to preserve clean `isError` results without relying on the SDK’s output-schema path.
- Mounting at `/mcp` still goes through a Starlette slash redirect to `/mcp/`; the protocol client handles it, but the behavior should be rechecked in the final review.

## Verification Plan

- Confirm the tool registers on the server.
- Verify a successful capture through an MCP client session.
- Verify semantic validation failures return `isError: true`.
- Verify unknown-tool calls raise protocol errors instead of tool results.
- Verify the storage-failure branch returns `isError: true`.

## Planned Commits

- `feat(mcp): implement capture_feedback tool`
