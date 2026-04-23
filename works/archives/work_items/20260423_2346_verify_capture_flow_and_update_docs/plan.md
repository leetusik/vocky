# Plan

- Work item: works/current/20260423_2346_verify_capture_flow_and_update_docs
- Created at: 20260423_2346
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.S5
- Slice: verify capture flow and update docs

## Context

- `P2.S4` completed the capture tool implementation and live protocol verification.
- The repo still lacks formal pytest coverage, user-facing run instructions, and updated durable docs that reflect the implemented capture path.
- The official MCP Python SDK testing helper is available at `mcp.shared.memory.create_connected_server_and_client_session`.

## Goal

Add the formal test suite and smoke coverage for the capture flow, then update README plus the architecture and API docs so the repo accurately documents the implemented service.

## Scope

- In scope:
  - Add validation-focused unit tests.
  - Add persistence tests against Postgres and MCP integration tests using the in-memory helper.
  - Re-run the compose smoke flow.
  - Update `README.md`, `docs/architecture.md`, and `docs/api.md`.
  - Update backlog state and record the slice result.
- Out of scope:
  - The final phase review slice.
  - New API surface beyond the capture tool.

## Approach

Build shared pytest fixtures around the async service and Alembic migration flow, add direct validation and in-memory MCP tests, rerun the compose smoke path, and then rewrite the user-facing docs so they match the actual implementation and commands.

## Affected Files

- `README.md`
- `docs/architecture.md`
- `docs/api.md`
- `tests/...`
- `works/backlog.md`
- `works/current/20260423_2346_verify_capture_flow_and_update_docs/plan.md`
- `works/current/20260423_2346_verify_capture_flow_and_update_docs/result.md`

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- Persistence tests need a reliable Postgres target without assuming the default local `5432` port is free.
- The docs should describe the actual `/mcp` endpoint behavior accurately, including the current redirect quirk if it remains.

## Verification Plan

- Run targeted pytest coverage for validation, persistence, and MCP integration.
- Re-run `make compose-up`, `make migrate`, `make smoke`, and `make compose-down` with the non-conflicting local port overrides.
- Review the updated README and reference docs for accuracy against the implemented behavior.

## Planned Commits

- `test(capture): add capture flow verification`
- `docs(readme): document local capture service workflow`
