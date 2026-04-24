# Plan

- Work item: works/current/20260424_1023_review_self_hosted_hardening_phase
- Created at: 20260424_1023
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.REVIEW
- Slice: phase review

## Context

- `P4.DECOMP`, `P4.S1`, `P4.S2`, and `P4.S3` are complete and archived.
- The phase now includes `.env`-driven Make targets, a documented Compose-first runbook, a readiness helper, fresh-install verification evidence from a clean checkout, and a verification-driven default PostgreSQL host-port update to `55432`.
- The review bar is to confirm there is no remaining drift between the backlog, Make workflow, `.env.example` defaults, README and architecture notes, and the recorded verification evidence.

## Goal

Review the completed `P4` phase against its operator-workflow and self-hosted acceptance criteria and either close the phase or surface explicit fix slices.

## Scope

- In scope:
- Recheck `Makefile`, `.env.example`, `README.md`, and `docs/architecture.md` for consistency around the supported `bootstrap` / `verify` flow, readiness waiting, and test-database isolation.
- Recheck `works/backlog.md` against the archived work items and final slice outcomes.
- Recheck the recorded fresh-install evidence in `P4.S3` and confirm it supports phase closure.
- Update `works/backlog.md` with the final review outcome and capture the result here.
- Out of scope:
- New implementation work unless the review finds concrete drift that requires a fix slice.
- Post-`P4` roadmap planning.

## Approach

Inspect the final repo state and the archived `P4` results together, verify that the documented self-hosted path matches the actual Make targets and recorded successful commands, and only mark the phase done if no fix slices are needed.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1023_review_self_hosted_hardening_phase/plan.md`
- `works/current/20260424_1023_review_self_hosted_hardening_phase/result.md`

## Reference Docs To Review

- `README.md`
- `.env.example`
- `Makefile`
- `docs/architecture.md`
- `works/backlog.md`
- `works/archives/work_items/20260424_1018_verify_fresh_self_hosted_flow/result.md`

## Risks and Open Questions

- The review should stay strict about the final operator story because the phase intentionally changed the supported defaults and workflow surface.
- The review needs to distinguish repo-tracked defaults from the user’s untracked local `.env`, which may still reflect older values outside the committed repo state.

## Verification Plan

- Re-read the final Make target definitions, `.env.example`, README, architecture notes, and `P4.S3` result.
- Confirm the repo-tracked PostgreSQL default port is consistently `55432` where applicable and that the test-database guard plus readiness behavior are both evidenced.

## Planned Commits

- None.
