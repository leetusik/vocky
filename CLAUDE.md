# CLAUDE.md

## Purpose

This repository defaults to agentic delivery via Claude Code or Codex. Claude Code reads this file directly; Codex reads `AGENTS.md`, which points here. Use planning, tracked work items, and review gates for almost all coding work. Backlog-scheduled work uses the full phase/slice workflow; unrelated user requests may use the Standalone Work path below.

## Commit Convention

- Format: `type(scope): summary` — `scope` optional, imperative summary, no trailing period.
- Supported types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `revert`.
- Examples: `feat(api): add feedback capture endpoint`, `fix(storage): handle empty values`.

## Python Development

- Use `uv` for Python development in this repository.
- Prefer `uv run` for Python commands such as tests, scripts, and CLIs.
- Prefer `uv add`, `uv remove`, `uv lock`, and `uv sync` for Python dependency management.
- Do not introduce `pip`, `venv`, or bare `python` workflows unless an existing repo constraint requires them.

## Working Model

- Almost all coding goes through plan + implement + review, not direct edits.
- `works/backlog.md` is the active queue of phases and slices; `works/deferred.md` is the parking lot.
- Active work-item folders live under `works/current/`; completed ones move to `works/archives/work_items/`.
- Archived backlog snapshots move to `works/archives/backlogs/`.
- Every backlog work item contains `plan.md` and `result.md`.
- Long-lived reference docs live under `docs/`; transient execution notes live under `works/`.
- Standalone unrelated requests do not require a phase, slice, or work-item folder.

## Stable IDs

- Phase IDs: `P1`, `P2`, `P3`, ...
- Slice IDs tied to phase: `P1.DECOMP` (decompose), `P1.S1`/`P1.S2` (middle), `P1.F1`/`P1.F2` (review-driven fix), `P1.REVIEW` (phase review).
- Reference phases and slices by ID in backlog entries, work-item files, and agent updates.

## Required Flow

1. Read `docs/product.md`, `docs/architecture.md`, `docs/api.md`, and `works/backlog.md`.
2. If every phase and slice in `works/backlog.md` is `done`, run `scripts/rotate_backlog.sh` (or `/rotate-backlog`) before selecting new backlog work.
3. If the request qualifies as Standalone Work, follow that section; do not create a phase or slice.
4. Choose or create the active phase in `works/backlog.md`.
5. Backlog creation is its own complete job: add phase entries with their mandatory `decompose phase` and `phase review` slices only — no middle slices, no implementation, no `decompose phase` execution. Stop after creation and report the new backlog.
6. Each new phase initially contains only `decompose phase` and `phase review`.
7. Run `scripts/start_work.sh <phase_id> <slice_id> <slug>` (or `/start-work`) to create a timestamped work-item folder.
8. Fill `plan.md` before code changes.
9. Implement the slice.
10. Fill `result.md` when implementation ends.
11. Run the `phase review` slice via the `phase-reviewer` subagent.
12. If review finds problems, create dedicated fix slices (`P<N>.F<n>`), implement them, rerun review.
13. Mark the phase `done` only after review passes.
14. When a `phase review` slice passes, archive every work item for that phase still under `works/current/` to `works/archives/work_items/`. **Phase-level archival is the only allowed trigger.** While a phase is `in_progress` or `in_review`, every work item bound to it stays under `works/current/`.
15. Use `scripts/archive_work.sh <work_dir_name>` (or `/archive-work`) only for the Step 14 sweep — never per-slice while the phase is open. When the sweep runs, update each affected slice's `Work item:` path in `works/backlog.md` from `works/current/...` to `works/archives/work_items/...`.
16. Run `scripts/rotate_backlog.sh` (or `/rotate-backlog`) when the active backlog cycle is finished.

## Standalone Work

- Applies when the request is unrelated to active backlog execution and does not explicitly ask to schedule backlog work.
- No phase, slice, or `works/current/` folder; do not run `scripts/start_work.sh`; do not add backlog entries to track it.
- If the backlog is already complete, run `scripts/rotate_backlog.sh` first as housekeeping; do not create a phase for the standalone request.
- Inspect relevant docs/code, make focused changes, run appropriate verification, report the result.
- For standalone changes that trigger reference-doc updates, update the relevant `docs/` files and summarize planned and completed doc changes in the final report instead of `plan.md`/`result.md`.

## Deferred Work

- `works/deferred.md` parks later jobs outside active execution order.
- If the user asks to save tasks, follow-ups, or ideas there, add them immediately — no phase/slice/work-item folder needed.
- During slice implementation, defer substantial later work that doesn't belong as a current slice, fix slice, or new phase. Never defer work required for the current slice or to pass the current phase review.
- Use the next stable `D<N>` ID. Record title, status, source, reason, and trigger for re-entry.
- Deferred jobs are not part of `do the next slice` / `do the whole phase` selection until promoted into `works/backlog.md`.

## Execution Commands

- `/do-next-slice` (or magic phrase `do the next slice`) — continue the current phase one slice at a time.
- `/do-whole-phase` (or magic phrase `do the whole phase`) — finish the current phase end-to-end, including review and fix slices. Limited to the current phase only.
- Resolve current phase: scan `works/backlog.md` top-to-bottom; first phase whose status is not `done`. If `blocked`, surface the blocker and stop.
- `do the next slice` selects the first slice in the current phase whose status is not `done`. Do not skip fix slices or `phase review` slices.
- `do the whole phase` may create one work item per slice as needed. The coordination work item (if any) stays open until all slice work items it initiated are complete; record the phase-level result last.
- If a matching active work item already exists for the selected phase/slice, continue it. Otherwise create one via `scripts/start_work.sh`.

## Status Model

- Phase: `planned`, `in_progress`, `in_review`, `blocked`, `done`.
- Slice: `todo`, `in_progress`, `in_review`, `changes_requested`, `done`.
- `phase review` cannot be marked `done` until the phase actually passes review. Use `changes_requested` when review found issues.

## Phase Review Stance

- Treat `phase review` as a skeptical audit, not a rubber stamp. Less-capable agents may have written the slices; do not assume correctness from plausible diffs or a tidy `result.md`.
- Verify behavior against the slice objective end-to-end, not whether files were touched.
- When review surfaces flaws, partial implementations, missed edge cases, or weak quality, create dedicated fix slices rather than letting the phase pass.
- Fix-slice instructions must be concrete: name exact files, functions, expected behavior, and edge cases. Vague guidance produces another underperforming pass.

## Backlog Rules

- Organize by phase, not as a flat task list. Keep `works/backlog.md` limited to actively scheduled work.
- Move intentionally deferred work to `works/deferred.md`; promote back when ready.
- Every phase must include objective, status, review outcome, work items, and slices.
- A new phase's slice list contains only `decompose phase` and `phase review`; no middle slices may pre-exist.
- Phase-level notes are allowed and encouraged for intent, constraints, assumptions, or handoff context. They are not slices.
- `decompose phase` is the only slice that may create the phase-specific middle slices needed to finish the phase.
- `phase review` validates the phase and stays open until the bar is met; re-review is mandatory after fixes.
- Prefix each slice with `[ ]` until done, then `[x]`. The checkbox is a visual summary; the `Status` field is authoritative.

## Fast-Path Exceptions

The full workflow is the default. A fast path is acceptable only for typo-only edits, one-line wording fixes, metadata-only changes, or tiny doc-only adjustments with no workflow impact. Never use the fast path when a change affects code behavior, tests, public or MCP-facing contracts, architecture, repository workflow, or multiple files with nontrivial intent.

## Reference Doc Update Triggers

- `docs/product.md` — when goals, users, terminology, scope, or product direction change.
- `docs/architecture.md` — when component boundaries, data flow, storage shape, runtime choices, or repo structure change.
- `docs/api.md` — when a public or MCP-facing contract is introduced, changed, stabilized, or deprecated.
- Record planned doc updates in `plan.md` and actual doc updates in `result.md` (or the final report for Standalone Work).

## Agent Tool Conventions

This workspace is dual-tool: Claude Code reads `CLAUDE.md` (this file); Codex reads `AGENTS.md`, which points to `CLAUDE.md`.

### Claude Code

- Slash commands live under `.claude/commands/`:
  - `/do-next-slice`, `/do-whole-phase` — backlog drivers.
  - `/start-work <phase_id> <slice_id> <slug>`, `/archive-work <work_dir_name>`, `/rotate-backlog` — workflow scripts.
  - `/commit` — group pending changes by topic and create one focused commit per group.
  - `/qa-check [mission_id_or_inline_brief]` — run the QA agent (requires a project-defined QA driver).
- Subagents live under `.claude/agents/`: `phase-reviewer.md`, `qa-agent.md`. Invoke via the `Agent` tool with `subagent_type: <name>`.
- Claude Code scans `.claude/agents/` at session start. Adding or editing a project subagent only takes effect after a full restart — `/clear` is not enough. If a subagent type is missing, the fallback subsections in `do-whole-phase.md` and `qa-check.md` describe a `general-purpose` invocation that inlines the policy body.
- Prefer Claude Code's built-in tools (`Read`, `Edit`, `Write`, `Glob`, `Grep`) over shelling to `cat`, `sed`, `awk`, `find` from `Bash`.

### Codex

- Codex reads `AGENTS.md`, which points to this file (`CLAUDE.md`). Project-level slash commands do not exist in Codex; named workflows are user-home only (`~/.codex/prompts/` or skills).
- Subagents are configured under `.codex/agents/*.toml`. Each TOML file bridges to its canonical Markdown policy at `.claude/agents/<name>.md`. Edit the policy, not the bridge.
- Codex users invoke the workflow by reading the relevant `CLAUDE.md` sections directly, or by wiring user-home skills that mirror the Claude Code slash commands.

## Reference Files

- `CLAUDE.md` — canonical workflow rules (this file).
- `AGENTS.md` — pointer to `CLAUDE.md` so Codex finds the policy by its native default name.
- `docs/product.md` — problem, users, goals, terminology.
- `docs/architecture.md` — current repo shape and intended system design.
- `docs/api.md` — current and planned public or MCP-facing contracts.
- `works/backlog.md` — actively scheduled phases and slices.
- `works/deferred.md` — parked jobs outside the active backlog.
- `works/templates/` — fresh templates for backlog, plan, and result.
- `.claude/commands/` — Claude Code slash commands.
- `.claude/agents/phase-reviewer.md` — phase-review gate policy.
- `.claude/agents/qa-agent.md` — mission-driven UI QA policy.
- `.codex/config.toml` — Codex project config.
- `.codex/agents/phase-reviewer.toml`, `.codex/agents/qa-agent.toml` — Codex bridges to the Markdown policies.

## Notes

- Keep product-facing messaging in `README.md`.
- Keep durable workflow rules in `CLAUDE.md`.
- Keep stable technical truth in `docs/`.
- Keep execution artifacts in `works/`.
