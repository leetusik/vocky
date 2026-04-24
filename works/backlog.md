# Backlog

## Status Model

- Phase: `planned`, `in_progress`, `in_review`, `blocked`, `done`
- Slice: `todo`, `in_progress`, `in_review`, `changes_requested`, `done`

## Usage Rules

- Every phase starts with `decompose phase` and `phase review`.
- Add phase-specific middle slices after `decompose phase` is completed.
- Keep `phase review` open until the phase passes review.
- If review fails, add dedicated fix slices and rerun review.
- Keep this file limited to actively scheduled phases and slices.
- Move intentionally deferred work into `works/deferred.md` instead of leaving it in the active backlog.
- Link active work items from `works/current/`.
- Use stable phase IDs such as `P1`.
- Use stable slice IDs such as `P1.DECOMP`, `P1.S1`, `P1.F1`, and `P1.REVIEW`.
- Prefix each slice with `[ ]` until it is done, then switch it to `[x]`.
- Treat the checkbox as a visual summary only. The `Status` field remains authoritative.

## Active Phases

### Phase P1: Explicit action feedback capture

- Phase ID: `P1`
- Objective: Extend Vocky's capture contract and storage so explicit user actions persist feedback value, comment, conversation messages, used context, channel, timestamps, and existing metadata.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260424_1632_decompose_action_feedback_mcp`
  - `works/archives/work_items/20260424_1633_add_action_feedback_storage_model`
  - `works/archives/work_items/20260424_1635_extend_capture_feedback_action_contract`
  - `works/archives/work_items/20260424_1636_update_capture_read_contracts_and_reference_docs`
  - `works/archives/work_items/20260424_1639_review_explicit_action_feedback_capture`
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260424_1632_decompose_action_feedback_mcp` | Notes: Locked the P1-P3 backlog structure and implementation order.
  - [x] Slice ID: `P1.S1` | Name: `add action feedback storage model` | Status: done | Work item: `works/archives/work_items/20260424_1633_add_action_feedback_storage_model` | Notes: Added first-class storage fields, migration, repository mapping, and persistence tests.
  - [x] Slice ID: `P1.S2` | Name: `extend capture_feedback action contract` | Status: done | Work item: `works/archives/work_items/20260424_1635_extend_capture_feedback_action_contract` | Notes: Extended capture input, validation, Redis serialization, and integration tests for action feedback.
  - [x] Slice ID: `P1.S3` | Name: `update capture/read contracts and reference docs` | Status: done | Work item: `works/archives/work_items/20260424_1636_update_capture_read_contracts_and_reference_docs` | Notes: Updated read filters, list record serialization, tests, and generic public docs.
  - [x] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260424_1639_review_explicit_action_feedback_capture` | Notes: Review passed with full pytest suite.

### Phase P2: Liked conversation retrieval and integration handoff

- Phase ID: `P2`
- Objective: Add a dedicated MCP read tool for AI agents to retrieve liked conversations as few-shot examples, plus integration docs for client apps.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260424_1639_decompose_liked_retrieval_and_handoff`
  - `works/archives/work_items/20260424_1640_add_liked_conversation_read_tool`
  - `works/archives/work_items/20260424_1641_write_general_action_feedback_integration_guide`
  - `works/archives/work_items/20260424_1642_write_gitignored_changple5_apply_handoff`
  - `works/archives/work_items/20260424_1643_review_liked_retrieval_and_handoff`
- Slices:
  - [x] Slice ID: `P2.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260424_1639_decompose_liked_retrieval_and_handoff` | Notes: Confirmed the liked-retrieval and documentation slices before implementation.
  - [x] Slice ID: `P2.S1` | Name: `add liked conversation read tool` | Status: done | Work item: `works/archives/work_items/20260424_1640_add_liked_conversation_read_tool` | Notes: Added liked-only MCP read surface with integration tests.
  - [x] Slice ID: `P2.S2` | Name: `write general action feedback integration guide` | Status: done | Work item: `works/archives/work_items/20260424_1641_write_general_action_feedback_integration_guide` | Notes: Added generic integration guide and public API docs for liked-conversation retrieval.
  - [x] Slice ID: `P2.S3` | Name: `write gitignored Changple5 apply handoff` | Status: done | Work item: `works/archives/work_items/20260424_1642_write_gitignored_changple5_apply_handoff` | Notes: Added local ignored handoff doc and confirmed it is ignored by git.
  - [x] Slice ID: `P2.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260424_1643_review_liked_retrieval_and_handoff` | Notes: Review passed with full pytest suite and ignored handoff check.

### Phase P3: Admin REST API for human review

- Phase ID: `P3`
- Objective: Implement dedicated REST API endpoints for human operators and admin dashboards, completely separate from MCP tools.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260424_1644_decompose_admin_rest_api`
  - `works/archives/work_items/20260424_1645_add_admin_rest_routing_surface`
  - `works/archives/work_items/20260424_1646_add_admin_feedback_query_endpoints`
  - `works/archives/work_items/20260424_1648_add_admin_feedback_management_endpoints`
  - `works/archives/work_items/20260424_1650_document_two_track_api_architecture`
  - `works/archives/work_items/20260424_1651_review_admin_rest_api`
- Slices:
  - [x] Slice ID: `P3.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260424_1644_decompose_admin_rest_api` | Notes: Locked route namespace, auth default, query endpoints, management endpoints, and docs scope.
  - [x] Slice ID: `P3.S1` | Name: `add admin REST routing surface` | Status: done | Work item: `works/archives/work_items/20260424_1645_add_admin_rest_routing_surface` | Notes: Added `/admin/api/*` Starlette routes and optional bearer protection without reusing MCP tool handlers.
  - [x] Slice ID: `P3.S2` | Name: `add admin feedback query endpoints` | Status: done | Work item: `works/archives/work_items/20260424_1646_add_admin_feedback_query_endpoints` | Notes: Added list/detail endpoints for all feedback, including likes, dislikes, comments, metadata, and full contexts.
  - [x] Slice ID: `P3.S3` | Name: `add admin feedback management endpoints` | Status: done | Work item: `works/archives/work_items/20260424_1648_add_admin_feedback_management_endpoints` | Notes: Added patch/delete management operations using the shared feedback service and repository.
  - [x] Slice ID: `P3.S4` | Name: `document two-track API architecture` | Status: done | Work item: `works/archives/work_items/20260424_1650_document_two_track_api_architecture` | Notes: Documented that MCP serves AI-agent workflows while Admin REST serves human/operator workflows over the same database schema.
  - [x] Slice ID: `P3.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260424_1651_review_admin_rest_api` | Notes: Review passed with full pytest suite.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
