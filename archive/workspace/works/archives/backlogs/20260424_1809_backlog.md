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

### Phase P1: Review fast-built feedback MCP/Admin backlog

- Phase ID: `P1`
- Objective: Review the completed P1-P3 work that was built too quickly, checking backlog quality, workflow compliance, code/API/docs consistency, tests, and any follow-up risks.
- Status: done
- Review outcome: passed
- Notes:
  - Review the prior action-feedback, liked-conversation retrieval, and Admin REST API work.
  - Check whether implementation matches docs and API contracts.
  - Check whether backlog/work-item history accurately represents what happened.
  - Identify needed fixes as explicit `P1.F*` slices during the audit and review work.
  - Do not implement fixes during backlog creation.
- Work items:
  - `works/archives/work_items/20260424_1716_decompose_review_fast_built_feedback_mcp_admin_backlog`
  - `works/archives/work_items/20260424_1720_audit_workflow_and_backlog_history`
  - `works/archives/work_items/20260424_1726_audit_mcp_feedback_contracts`
  - `works/archives/work_items/20260424_1728_audit_admin_rest_contracts`
  - `works/archives/work_items/20260424_1729_verify_test_posture_and_follow_up_risks`
  - `works/archives/work_items/20260424_1730_archive_fast_built_backlog_snapshot`
  - `works/archives/work_items/20260424_1731_review_fast_built_feedback_mcp_admin_backlog`
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260424_1716_decompose_review_fast_built_feedback_mcp_admin_backlog` | Notes: Defined separate workflow, MCP contract, Admin REST contract, and test/risk review slices.
  - [x] Slice ID: `P1.S1` | Name: `audit workflow and backlog history` | Status: done | Work item: `works/archives/work_items/20260424_1720_audit_workflow_and_backlog_history` | Notes: Found one actionable workflow-history gap: the completed fast-built P1-P3 backlog needs an archived snapshot before final review.
  - [x] Slice ID: `P1.S2` | Name: `audit MCP feedback contracts` | Status: done | Work item: `works/archives/work_items/20260424_1726_audit_mcp_feedback_contracts` | Notes: MCP implementation, tests, README, integration guide, `docs/api.md`, and architecture notes are consistent; no required fix slice identified.
  - [x] Slice ID: `P1.S3` | Name: `audit Admin REST contracts` | Status: done | Work item: `works/archives/work_items/20260424_1728_audit_admin_rest_contracts` | Notes: Admin REST implementation, tests, README, `docs/api.md`, and architecture notes are consistent; no required fix slice identified.
  - [x] Slice ID: `P1.S4` | Name: `verify test posture and follow-up risks` | Status: done | Work item: `works/archives/work_items/20260424_1729_verify_test_posture_and_follow_up_risks` | Notes: Full pytest baseline passes with meaningful coverage of the reviewed MVP risks; no additional fix slice identified.
  - [x] Slice ID: `P1.F1` | Name: `archive fast-built backlog snapshot` | Status: done | Work item: `works/archives/work_items/20260424_1730_archive_fast_built_backlog_snapshot` | Notes: Preserved the completed action-feedback, liked-conversation, and Admin REST P1-P3 backlog from `HEAD:works/backlog.md` as `works/archives/backlogs/20260424_1652_backlog.md`.
  - [x] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260424_1731_review_fast_built_feedback_mcp_admin_backlog` | Notes: Review passed after workflow, MCP, Admin REST, test/risk, and backlog snapshot checks; no follow-up fix slices required.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
