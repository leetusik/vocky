# Result

- Work item: works/current/20260429_1110_refresh_public_capture_guidance_compatibility
- Created at: 20260429_1110
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S4
- Slice: refresh public capture guidance and compatibility coverage
- Review status: passed
- Reviewer: Codex
- Next action: Archive this work item and continue with `P1.REVIEW`.

## Outcome

Refreshed public guidance in `README.md` and `docs/action-feedback-integration.md` so MCP is framed as agent-decided VoC capture and REST is framed as explicit server-to-server product/UI feedback capture. The docs now describe `target_type` as the review discriminator for `message`, `conversation`, and `surface` feedback and state that older unset records remain visible unless an exact type filter is applied.

Adjusted the existing message and surface examples without changing tool names, endpoint names, capture fields, or storage shape. Added REST compatibility coverage for omitted `target_type` payloads enqueueing with null target fields.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_capture_validation.py tests/test_capture_api.py tests/test_mcp_integration.py tests/test_persistence.py` passed, 49 tests.
- `git diff --check` passed.

## Files changed

- `README.md`
- `docs/action-feedback-integration.md`
- `tests/test_capture_api.py`

## Docs updated

- `README.md`: clarified MCP-vs-REST capture intent, `target_type` review filtering, and unset-target compatibility.
- `docs/action-feedback-integration.md`: clarified surface selection, examples, `target_type` filtering, and older-capture compatibility.

## Roadmap updates

- `P1.S4` can be marked done. Continue with `P1.REVIEW`.

## Retrospective

- Existing examples were close; the main gap was making the intended capture surface split explicit and documenting null-target compatibility in public-facing guidance.
