# Plan

- Work item: works/current/20260427_1808_separate_transport_capture_input_paths
- Created at: 20260427_1808
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.S2
- Slice: separate transport capture input paths

## Goal

Split MCP and REST capture input handling at the adapter boundary so each transport can express its own intent, while preserving the shared queue payload, service layer, persistence model, validation semantics, and accepted receipt shape.

## Scope

- Update `src/vocky/capture.py` with explicit MCP and REST raw input models plus transport-named normalizers.
- Update `src/vocky/tools/capture_feedback.py` to construct the MCP-specific input model and call the MCP normalizer.
- Update `src/vocky/api.py` to parse REST bodies into the REST-specific input model and call the REST normalizer.
- Update focused validation tests for the new names and shared behavior.
- Do not change storage, migrations, queue serialization, public endpoint paths, receipt shape, auth, Admin REST, or read tools.

## Context

- `P2.S1` locked the public direction: REST broadens through existing fields only.
- Current code has a single `CaptureFeedbackInput` and `normalize_payload` shared by REST and MCP.
- The implementation should avoid behavior changes for currently accepted REST and MCP payloads.
- Compatibility aliases can remain where cheap, but production adapter code should use transport-specific names.

## Milestones

1. Mark `P2.S2` in progress and link this work item from `works/backlog.md`.
2. Add transport-specific input models and normalizers in `src/vocky/capture.py`.
3. Update REST and MCP adapters to use their specific model/normalizer names.
4. Update focused tests for capture validation and existing adapter behavior.
5. Run targeted tests and close the slice.

## Validation

- `uv run pytest tests/test_capture_validation.py tests/test_capture_api.py tests/test_mcp_integration.py`

## Risks / open questions

- Risk: Pydantic/MCP schema generation could change unexpectedly if the tool parameter model changes. Keep the `source` nested model stable.
- Risk: Import churn could break existing tests. Keep low-cost compatibility aliases in `vocky.capture`.

## Docs to update

- None in this slice. Durable docs were updated in `P2.S1`; user-facing examples are scheduled for `P2.S3`.
