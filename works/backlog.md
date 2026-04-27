# Backlog

## Status Model

- Phase: `planned`, `in_progress`, `in_review`, `blocked`, `done`
- Slice: `todo`, `in_progress`, `in_review`, `changes_requested`, `done`

## Usage Rules

- Every newly created phase starts with only `decompose phase` and `phase review`.
- Phase-level notes are allowed and encouraged; they do not count as slices.
- Do not pre-seed phase-specific middle slices in a newly created backlog.
- Add phase-specific middle slices only from the dedicated `decompose phase` slice.
- Keep `phase review` open until the phase passes review.
- If review fails, add dedicated fix slices and rerun review.
- Keep this file limited to actively scheduled phases and slices.
- This file schedules backlog-driven phases and slices only; unrelated standalone requests do not need phase, slice, or work-item entries.
- Move intentionally deferred work into `works/deferred.md` instead of leaving it in the active backlog.
- Link active work items from `works/current/`.
- If every documented phase is `done` and every documented slice is `done`, run `scripts/rotate_backlog.sh` before starting new backlog-scheduled work.
- `scripts/rotate_backlog.sh` archives the active `works/backlog.md` file to `works/archives/backlogs/<timestamp>_backlog.md` and replaces it from `works/templates/backlog.md`.
- If the next request is standalone, completed-backlog rotation is housekeeping only and does not create a phase or slice for that request.
- Use stable phase IDs such as `P1`.
- Use stable slice IDs such as `P1.DECOMP`, `P1.S1`, `P1.F1`, and `P1.REVIEW`.
- Prefix each slice with `[ ]` until it is done, then switch it to `[x]`.
- Treat the checkbox as a visual summary only. The `Status` field remains authoritative.

## Active Phases

### Phase P1: Feedback context and target semantics

- Phase ID: `P1`
- Objective: Clarify feedback context identifiers and make the exact message or product surface being reviewed explicit instead of assuming the latest message.
- Status: done
- Review outcome: passed
- Notes: Treat `conversation_id` as conversation/thread scope and `session_id` as optional runtime or user-session scope unless decomposition finds a better naming model. Message-specific feedback should identify the exact user or assistant message, selected message context, or explicit non-message feedback target.
- Work items:
  - `works/archives/work_items/20260427_1537_decompose_feedback_context_target_semantics`
  - `works/archives/work_items/20260427_1708_lock_feedback_context_terminology`
  - `works/archives/work_items/20260427_1712_add_explicit_feedback_target_capture_model`
  - `works/archives/work_items/20260427_1716_surface_target_context_in_review_flows`
  - `works/archives/work_items/20260427_1721_update_integration_guidance_and_compatibility_tests`
  - `works/archives/work_items/20260427_1723_review_feedback_context_target_semantics`
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260427_1537_decompose_feedback_context_target_semantics` | Notes: Added concrete terminology, target-model, review-surface, guidance, and compatibility slices for P1.
  - [x] Slice ID: `P1.S1` | Name: `lock feedback context terminology` | Status: done | Work item: `works/archives/work_items/20260427_1708_lock_feedback_context_terminology` | Notes: Defined `conversation_id`, `session_id`, the current `message` meaning, and explicit feedback-target semantics in product, API, and architecture docs before code changes.
  - [x] Slice ID: `P1.S2` | Name: `add explicit feedback target capture model` | Status: done | Work item: `works/archives/work_items/20260427_1712_add_explicit_feedback_target_capture_model` | Notes: Added nullable target fields through validation, queue payloads, service types, persistence, migration, and capture contracts while keeping existing captures compatible.
  - [x] Slice ID: `P1.S3` | Name: `surface target context in review flows` | Status: done | Work item: `works/archives/work_items/20260427_1716_surface_target_context_in_review_flows` | Notes: Returned target fields through MCP read tools and Admin REST, and showed exact target context in Admin UI list and detail views.
  - [x] Slice ID: `P1.S4` | Name: `update integration guidance and compatibility tests` | Status: done | Work item: `works/archives/work_items/20260427_1721_update_integration_guidance_and_compatibility_tests` | Notes: Updated examples and docs to show exact message targeting and covered old payloads, new target payloads, and conversation/session semantics.
  - [x] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260427_1723_review_feedback_context_target_semantics` | Notes: Review passed with full pytest and package asset checks; no fix slices were needed.

### Phase P2: Separate REST and MCP capture intent

- Phase ID: `P2`
- Objective: Make REST capture support general website or product feedback while MCP capture remains optimized for message-specific agent feedback.
- Status: done
- Review outcome: passed
- Notes: REST capture remains server-to-server. Do not add browser-direct unauthenticated ingestion in this backlog. Adapt the existing `POST /api/feedback` contract in place for broader website/product feedback while preserving compatibility for current accepted REST payloads; do not add a versioned or split REST endpoint in P2.
- Work items:
  - `works/archives/work_items/20260427_1800_decompose_rest_mcp_capture_intent`
  - `works/archives/work_items/20260427_1806_lock_rest_mcp_capture_contract_split`
  - `works/archives/work_items/20260427_1808_separate_transport_capture_input_paths`
  - `works/archives/work_items/20260427_1811_update_rest_general_feedback_examples_and_compatibility`
  - `works/archives/work_items/20260427_1813_review_rest_mcp_capture_intent`
- Slices:
  - [x] Slice ID: `P2.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260427_1800_decompose_rest_mcp_capture_intent` | Notes: Added contract, transport-separation, guidance, and compatibility slices for P2.
  - [x] Slice ID: `P2.S1` | Name: `lock REST and MCP capture contract split` | Status: done | Work item: `works/archives/work_items/20260427_1806_lock_rest_mcp_capture_contract_split` | Notes: Durable docs now define REST as broader server-to-server website/product feedback through the existing fields, while MCP remains agent/message-oriented.
  - [x] Slice ID: `P2.S2` | Name: `separate transport capture input paths` | Status: done | Work item: `works/archives/work_items/20260427_1808_separate_transport_capture_input_paths` | Notes: Added explicit MCP and REST capture input models/normalizers while preserving shared queue, service, persistence, validation behavior, and receipt shape.
  - [x] Slice ID: `P2.S3` | Name: `update REST general-feedback examples and compatibility coverage` | Status: done | Work item: `works/archives/work_items/20260427_1811_update_rest_general_feedback_examples_and_compatibility` | Notes: Added website/product REST examples and tests proving current message/action payloads and broader surface feedback payloads are accepted without exposing new public review endpoints.
  - [x] Slice ID: `P2.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260427_1813_review_rest_mcp_capture_intent` | Notes: Review passed with full pytest, package asset checks, and Compose-backed verify after rebuilding the stale app/worker containers; no fix slices were needed.

### Phase P3: Channel categories and Admin adjustability

- Phase ID: `P3`
- Objective: Replace free-text-only `channel` handling with nullable, default-none category behavior that operators can adjust in Admin.
- Status: planned
- Review outcome: pending
- Notes: Decomposition should cover storage and migration shape, API validation, query filters, Admin list/detail/edit behavior, and how allowed categories are represented or managed.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P3.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P3.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

### Phase P4: Working REST capture Try docs

- Phase ID: `P4`
- Objective: Add Swagger-like in-app REST capture documentation with a real try-it request flow.
- Status: planned
- Review outcome: pending
- Notes: Build this after REST semantics are stable. The try feature should call the real REST capture endpoint, support the configured bearer token, show request, response, and error output, and include examples for general website feedback such as `피드백을 보내주세요!`.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P4.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P4.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
- Fresh backlog contents come from `works/templates/backlog.md`.
