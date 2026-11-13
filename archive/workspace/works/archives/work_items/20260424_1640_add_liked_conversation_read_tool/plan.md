# Plan

- Work item: works/current/20260424_1640_add_liked_conversation_read_tool
- Created at: 20260424_1640
- Phase ID: P2
- Phase: Liked conversation retrieval and integration handoff
- Slice ID: P2.S1
- Slice: add liked conversation read tool

## Context

P1 added `feedback_value=1` for likes and `feedback_value=2` for dislikes. AI agents need a dedicated MCP read tool for liked conversations as few-shot examples, while human/operator review will be handled by P3 Admin REST.

## Goal

Add `list_liked_conversations` as an MCP read tool that returns only liked feedback records with messages, used context, comments, and metadata.

## Scope

- In scope: New MCP tool, tool registration, filters, cursor pagination, serialization, and MCP integration tests.
- Out of scope: Semantic/syntax retrieval, Admin REST routes, and docs beyond minimal API registration comments.

## Approach

Reuse the existing service/repository query path with `feedback_value=1` enforced server-side. Support ingest-time, source, conversation/session, channel, and tag filters plus the existing cursor pagination.

## Affected Files

- `src/vocky/tools/list_liked_conversations.py`
- `src/vocky/mcp_server.py`
- `tests/test_mcp_integration.py`

## Reference Docs To Review

- `docs/api.md`

## Risks and Open Questions

- The tool must never return dislikes even when filters match other dimensions.
- This tool is AI-agent oriented and should not become the human admin query surface.

## Verification Plan

- Add an MCP integration test proving likes are returned and dislikes are excluded.
- Run MCP integration and query validation tests.

## Planned Commits

- Not committing unless requested.
