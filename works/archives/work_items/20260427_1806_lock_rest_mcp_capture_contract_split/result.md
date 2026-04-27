# Result

- Work item: works/current/20260427_1806_lock_rest_mcp_capture_contract_split
- Created at: 20260427_1806
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.S1
- Slice: lock REST and MCP capture contract split
- Review status: completed
- Reviewer: Codex
- Next action: Start `P2.S2` to split transport-specific capture input paths.

## Outcome

Locked the durable P2 contract direction in product, architecture, and API docs. REST capture is now documented as broader server-to-server website/product feedback using the existing capture fields, while MCP capture remains framed around agent/message workflows.

## Deviations from plan

None.

## Validation run

- Inspected `docs/product.md`, `docs/architecture.md`, and `docs/api.md` for consistent REST/MCP wording.
- Confirmed the docs say REST uses existing fields only, stays server-to-server, and remains capture-only.
- No code tests were run because this slice only changed docs and workflow artifacts.

## Files changed

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`
- `works/current/20260427_1806_lock_rest_mcp_capture_contract_split/plan.md`
- `works/current/20260427_1806_lock_rest_mcp_capture_contract_split/result.md`

## Docs updated

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Roadmap updates

- Marked `P2.S1` complete in `works/backlog.md`.

## Retrospective

- Keeping REST broadening on existing fields avoids migration and compatibility risk for the next implementation slice.
