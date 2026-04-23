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

## Active Phases

### Phase P1: <phase name>

- Phase ID: `P1`
- Objective: <what this phase should accomplish>
- Status: planned
- Review outcome: pending
- Work items:
  - None yet
- Slices:
  - Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - Slice ID: `P1.S1` | Name: `<middle slice>` | Status: todo | Work item: none | Notes: Replace this line with the first phase-specific slice.
  - Slice ID: `P1.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
