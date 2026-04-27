# Plan

- Work item: works/current/20260427_1407_decompose_feedback_review_management
- Created at: 20260427_1407
- Phase ID: P4
- Phase: Feedback review and management
- Slice ID: P4.DECOMP
- Slice: decompose phase

## Goal

Break `P4` into concrete, ordered implementation slices for the Feedback view so later work can build the review and management workflow without deciding scope or sequencing during execution.

## Scope

- In scope: update `works/backlog.md` for `P4`, mark `P4.DECOMP` complete, link this work item, and add middle implementation slices before `P4.REVIEW`.
- Out of scope: application code, tests, UI assets, reference-doc edits, or Admin REST contract changes.

## Context

- `P1` added the Admin Web UI shell, `P2` added in-app operator docs, and `P3` added dashboard metrics and recent activity.
- The Feedback view still contains a placeholder surface.
- Admin REST already provides protected list, detail, patch, and delete endpoints under `/admin/api/*`.
- P4 should stay operator-focused and avoid SaaS account, organization, billing, or tenant-selection concepts.

## Milestones

1. Link this work item in the `P4` work-item list.
2. Mark `P4` as `in_progress` and `P4.DECOMP` as `done`.
3. Add the feedback list/filter slice.
4. Add the feedback detail inspection slice.
5. Add the review-field editing slice.
6. Add the delete flow and docs polish slice.
7. Leave `P4.REVIEW` open after the new implementation slices.

## Validation

- Inspect `works/backlog.md` and confirm the final `P4` slice order is `P4.DECOMP`, `P4.S1`, `P4.S2`, `P4.S3`, `P4.S4`, and `P4.REVIEW`.
- Confirm every new slice has a stable ID, checkbox, status, work item field, and actionable notes.
- Confirm no application code, tests, UI assets, or reference docs were changed by this decomposition slice.

## Risks / open questions

- Future slices should reuse existing Admin REST contracts instead of adding a browser-specific API.
- `source_metadata` and `attributes` should remain visible but read-only in the first Feedback UI workflow unless a future slice explicitly changes scope.
- Delete should require an explicit guarded UI action in the future implementation slice because it permanently removes records through the existing Admin REST endpoint.

## Docs to update

- None in this decomposition slice.
- Future `P4.S4` should update README, product/architecture docs, and in-app docs wording when the Feedback review workflow becomes implemented.
