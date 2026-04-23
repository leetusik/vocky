# Backlog

## Status Model

- Phase: `planned`, `in_progress`, `in_review`, `blocked`, `done`
- Slice: `todo`, `in_progress`, `in_review`, `changes_requested`, `done`

## Usage Rules

- Every phase starts with `decompose phase` and `phase review`.
- Add phase-specific middle slices after `decompose phase` is completed.
- Keep `phase review` open until the phase passes review.
- If review fails, add dedicated fix slices and rerun review.
- Link active work items from `works/current/`.
- Use stable phase IDs such as `P1`.
- Use stable slice IDs such as `P1.DECOMP`, `P1.S1`, `P1.F1`, and `P1.REVIEW`.
- Prefix each slice with `[ ]` until it is done, then switch it to `[x]`.
- Treat the checkbox as a visual summary only. The `Status` field remains authoritative.

## Active Phases

### Phase P1: Lock MVP scope and draft contracts

- Phase ID: `P1`
- Objective: Turn the approved first-MVP direction into concrete product, architecture, and contract docs so implementation can start without reopening scope decisions.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260423_1814_mvp_phase_planning`
  - `works/archives/work_items/20260423_1816_lock_mvp_product_scope`
  - `works/archives/work_items/20260423_1817_draft_mvp_architecture_and_contracts`
  - `works/archives/work_items/20260423_1819_review_mvp_scope_phase`
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260423_1814_mvp_phase_planning` | Notes: Replace the placeholder backlog with the first-MVP roadmap and define the middle slices for `P1`.
  - [x] Slice ID: `P1.S1` | Name: `lock MVP product scope` | Status: done | Work item: `works/archives/work_items/20260423_1816_lock_mvp_product_scope` | Notes: Update product-facing docs to define the self-hosted, MCP-only MVP scope and explicit deferrals.
  - [x] Slice ID: `P1.S2` | Name: `draft MVP architecture and contracts` | Status: done | Work item: `works/archives/work_items/20260423_1817_draft_mvp_architecture_and_contracts` | Notes: Update architecture and API docs for MCP capture, storage, and minimal review/query surfaces.
  - [x] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260423_1819_review_mvp_scope_phase` | Notes: Reviewed the phase docs for consistency and closed the phase with no fix slices required.

### Phase P5: Update workflow rules for execution and slice tracking

- Phase ID: `P5`
- Objective: Add durable workflow rules for `uv`, `go`-driven next-slice handling, and clearer slice presentation before implementation phases begin.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260423_1821_workflow_rule_updates`
  - `works/archives/work_items/20260423_1822_update_agent_workflow_rules`
  - `works/archives/work_items/20260423_1823_apply_checkbox_slice_format`
  - `works/archives/work_items/20260423_1824_review_workflow_rule_phase`
- Slices:
  - [x] Slice ID: `P5.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260423_1821_workflow_rule_updates` | Notes: Added the concrete workflow-rule and backlog-format slices required to complete the phase.
  - [x] Slice ID: `P5.S1` | Name: `update agent workflow rules` | Status: done | Work item: `works/archives/work_items/20260423_1822_update_agent_workflow_rules` | Notes: Added durable AGENTS rules for `uv`-based Python work, `go`-driven next-slice selection, and checkbox-backed slice tracking.
  - [x] Slice ID: `P5.S2` | Name: `apply checkbox slice format` | Status: done | Work item: `works/archives/work_items/20260423_1823_apply_checkbox_slice_format` | Notes: Updated the active backlog and backlog template so slice lines use explicit checkbox markers.
  - [x] Slice ID: `P5.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260423_1824_review_workflow_rule_phase` | Notes: Reviewed the workflow-rule updates, confirmed the new rules are consistent, and closed the phase.

### Phase P6: Refine go-command workflow navigation

- Phase ID: `P6`
- Objective: Make `go`, `go next slice`, and `go next phase` resolve predictably in the tracked workflow before implementation phases begin.
- Status: done
- Review outcome: passed
- Work items:
  - `works/archives/work_items/20260423_1826_refine_go_navigation`
  - `works/archives/work_items/20260423_1827_refine_go_command_rules`
  - `works/archives/work_items/20260423_1828_review_go_navigation_phase`
- Slices:
  - [x] Slice ID: `P6.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260423_1826_refine_go_navigation` | Notes: Added the concrete go-command rule-update slice required to finish the phase.
  - [x] Slice ID: `P6.S1` | Name: `refine go command rules` | Status: done | Work item: `works/archives/work_items/20260423_1827_refine_go_command_rules` | Notes: Updated `AGENTS.md` so bare `go` defaults to `go next slice`, and defined explicit behavior for `go next slice` and `go next phase`.
  - [x] Slice ID: `P6.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260423_1828_review_go_navigation_phase` | Notes: Reviewed the go-command updates, confirmed the command semantics are coherent, and closed the phase.

### Phase P2: Build MCP capture and persistence core

- Phase ID: `P2`
- Objective: Implement the first usable path from MCP feedback submission to persisted feedback records with validation and predictable errors.
- Status: planned
- Review outcome: pending
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P2.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break the capture and persistence phase into concrete implementation and review slices.
  - [ ] Slice ID: `P2.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the completed capture and persistence work, add fix slices if needed, and rerun until it passes.

### Phase P3: Build review/query API

- Phase ID: `P3`
- Objective: Expose stored feedback through a minimal review/query API that supports record retrieval and simple counts or trends.
- Status: planned
- Review outcome: pending
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P3.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break the review/query API phase into concrete implementation and review slices.
  - [ ] Slice ID: `P3.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the completed review/query work, add fix slices if needed, and rerun until it passes.

### Phase P4: Harden the self-hosted MVP

- Phase ID: `P4`
- Objective: Make the MVP runnable end-to-end for self-hosted users with setup guidance, configuration clarity, and final verification.
- Status: planned
- Review outcome: pending
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P4.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break the hardening phase into concrete setup, verification, and review slices.
  - [ ] Slice ID: `P4.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the completed hardening work, add fix slices if needed, and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
