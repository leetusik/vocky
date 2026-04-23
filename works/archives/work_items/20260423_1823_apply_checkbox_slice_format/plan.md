# Plan

- Work item: works/current/20260423_1823_apply_checkbox_slice_format
- Created at: 20260423_1823
- Phase ID: P5
- Phase: Update workflow rules for execution and slice tracking
- Slice ID: P5.S2
- Slice: apply checkbox slice format

## Context

`AGENTS.md` now defines `[ ]` and `[x]` as the visual slice markers, but the active backlog and backlog template still use the older plain list format.

## Goal

Apply the checkbox-based slice presentation to the active backlog and to the backlog template so future work starts with the new format by default.

## Scope

- In scope:
  - Update `works/backlog.md` usage rules for checkbox markers
  - Convert all slice entries in `works/backlog.md` to the checkbox format
  - Update `works/templates/backlog.md` to use the checkbox format in new backlogs
- Out of scope:
  - Changing phase objectives or scope
  - Starting the review slice or the next product phase

## Approach

Keep the checkbox markers binary: `[x]` when a slice is done and `[ ]` otherwise. Preserve the detailed `Status` field so in-progress and changes-requested states remain explicit.

## Affected Files

- works/backlog.md
- works/templates/backlog.md

## Reference Docs To Review

- AGENTS.md
- works/backlog.md
- works/templates/backlog.md

## Risks and Open Questions

- The current backlog and template need to stay structurally aligned so the new rule is not only documented but also used in practice.

## Verification Plan

- Review both backlog files to confirm every slice line has the right checkbox marker.
- Confirm the active backlog points to the archived `P5.S1` work item and the current `P5.S2` work item.

## Planned Commits

- docs(workflow): add checkbox slice markers
