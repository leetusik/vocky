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

### Phase P1: Clarify capture surfaces and feedback type separation

- Phase ID: `P1`
- Objective: Reposition Vocky capture guidance so MCP is for agent-decided VoC capture, REST is the first-choice path for explicit product/UI-triggered capture, and message versus non-message feedback is separated through `target_type` without splitting storage.
- Status: in_progress
- Review outcome: pending
- Notes:
  - Keep the current `feedback_events` table as the canonical feedback store.
  - Use `target_type="message"` for message feedback.
  - Use `target_type="surface"` for concrete non-message product or website surface feedback; leave `target_type` null when no exact target type is known.
  - Add `target_type` as a supported read/filter dimension and index before treating message/general feedback as separately reviewable categories.
  - Do not rename existing MCP tools, REST endpoints, or capture fields in this phase.
  - Reconsider split tables only if lifecycle, permissions, retention, required schema, or query performance diverge materially.
- Work items:
  - `works/archives/work_items/20260429_1046_decompose_capture_surfaces_feedback_type_separation`
  - `works/archives/work_items/20260429_1052_lock_capture_boundary_type_contract`
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260429_1046_decompose_capture_surfaces_feedback_type_separation` | Notes: Added contract, read-filter/index, Admin workflow/docs, public guidance/coverage, and review slices for P1.
  - [x] Slice ID: `P1.S1` | Name: `lock capture boundary and type contract` | Status: done | Work item: `works/archives/work_items/20260429_1052_lock_capture_boundary_type_contract` | Notes: Locked durable product/API/architecture direction for MCP agent-decided capture, REST explicit product/UI capture, and single-table `target_type` review separation before code changes.
  - [ ] Slice ID: `P1.S2` | Name: `add target_type read filters and index` | Status: todo | Work item: none | Notes: Implement `target_type` filtering across MCP/Admin read paths and add a PostgreSQL index without adding new storage tables or feedback-kind fields.
  - [ ] Slice ID: `P1.S3` | Name: `update Admin type filtering and operator docs` | Status: todo | Work item: none | Notes: Add Admin UI type-filter behavior and packaged operator docs/examples for message versus surface/general feedback review.
  - [ ] Slice ID: `P1.S4` | Name: `refresh public capture guidance and compatibility coverage` | Status: todo | Work item: none | Notes: Update README/action integration guidance, examples, tests, and smoke wording around MCP-versus-REST intent and target-type compatibility.
  - [ ] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
- Fresh backlog contents come from `works/templates/backlog.md`.
