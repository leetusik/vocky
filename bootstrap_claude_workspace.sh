#!/bin/sh
set -eu

usage() {
  cat <<'USAGE'
Usage:
  bootstrap_claude_workspace.sh [TARGET_DIR] [options]

Options:
  --name NAME                 Project name for starter docs
  --summary TEXT              One-sentence product summary
  --phase-name NAME           Initial P1 phase name
  --phase-objective TEXT      Initial P1 phase objective
  -h, --help                  Show this help

TARGET_DIR defaults to the current directory. The script is fresh-only: it
refuses to overwrite managed workflow files if they already exist.

Bootstraps a dual-tool (Claude Code + Codex) agentic workspace:
AGENTS.md (canonical) + CLAUDE.md (pointer), docs/, works/, scripts/,
plus .claude/commands/, .claude/agents/, and .codex/ bridges.
USAGE
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

need_value() {
  [ $# -ge 2 ] || die "$1 requires a value"
  [ -n "$2" ] || die "$1 requires a non-empty value"
}

prompt_value() {
  label=$1
  default=$2

  if [ -t 0 ]; then
    printf '%s [%s]: ' "$label" "$default" >&2
    IFS= read -r value || value=
    if [ -n "$value" ]; then
      printf '%s\n' "$value"
    else
      printf '%s\n' "$default"
    fi
  else
    printf '%s\n' "$default"
  fi
}

target_dir=
project_name=
project_summary=
phase_name=
phase_objective=

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --name)
      need_value "$1" "${2-}"
      project_name=$2
      shift 2
      ;;
    --name=*)
      project_name=${1#--name=}
      [ -n "$project_name" ] || die "--name requires a non-empty value"
      shift
      ;;
    --summary)
      need_value "$1" "${2-}"
      project_summary=$2
      shift 2
      ;;
    --summary=*)
      project_summary=${1#--summary=}
      [ -n "$project_summary" ] || die "--summary requires a non-empty value"
      shift
      ;;
    --phase-name)
      need_value "$1" "${2-}"
      phase_name=$2
      shift 2
      ;;
    --phase-name=*)
      phase_name=${1#--phase-name=}
      [ -n "$phase_name" ] || die "--phase-name requires a non-empty value"
      shift
      ;;
    --phase-objective)
      need_value "$1" "${2-}"
      phase_objective=$2
      shift 2
      ;;
    --phase-objective=*)
      phase_objective=${1#--phase-objective=}
      [ -n "$phase_objective" ] || die "--phase-objective requires a non-empty value"
      shift
      ;;
    --)
      shift
      while [ $# -gt 0 ]; do
        [ -z "$target_dir" ] || die "only one TARGET_DIR may be provided"
        target_dir=$1
        shift
      done
      ;;
    -*)
      die "unknown option $1"
      ;;
    *)
      [ -z "$target_dir" ] || die "only one TARGET_DIR may be provided"
      target_dir=$1
      shift
      ;;
  esac
done

[ -n "$target_dir" ] || target_dir=.

if [ -e "$target_dir" ] && [ ! -d "$target_dir" ]; then
  die "target exists but is not a directory: $target_dir"
fi

if [ "$target_dir" = "." ]; then
  default_name=$(basename "$(pwd)")
else
  default_name=$(basename "$target_dir")
fi

case "$default_name" in
  ""|"."|"/")
    default_name="New Project"
    ;;
esac

[ -n "$project_name" ] || project_name=$(prompt_value "Project name" "$default_name")
[ -n "$project_summary" ] || project_summary=$(prompt_value "Project summary" "Describe what this project is for.")
[ -n "$phase_name" ] || phase_name=$(prompt_value "Initial phase name" "Project Foundation")
[ -n "$phase_objective" ] || phase_objective=$(prompt_value "Initial phase objective" "Define the initial product, architecture, API surface, and first implementation slices for $project_name.")

managed_dirs='
docs
works
works/templates
works/current
works/archives
works/archives/backlogs
works/archives/work_items
scripts
.claude
.claude/commands
.claude/agents
.codex
.codex/agents
'

managed_files='
AGENTS.md
CLAUDE.md
docs/product.md
docs/architecture.md
docs/api.md
works/backlog.md
works/deferred.md
works/templates/backlog.md
works/templates/plan.md
works/templates/result.md
scripts/start_work.sh
scripts/archive_work.sh
scripts/rotate_backlog.sh
.claude/commands/do-next-slice.md
.claude/commands/do-whole-phase.md
.claude/commands/start-work.md
.claude/commands/archive-work.md
.claude/commands/rotate-backlog.md
.claude/commands/commit.md
.claude/commands/qa-check.md
.claude/agents/phase-reviewer.md
.claude/agents/qa-agent.md
.codex/config.toml
.codex/agents/phase-reviewer.toml
.codex/agents/qa-agent.toml
'

mkdir -p "$target_dir"

for dir in $managed_dirs; do
  if [ -e "$target_dir/$dir" ] && [ ! -d "$target_dir/$dir" ]; then
    die "managed directory path exists but is not a directory: $dir"
  fi
done

conflicts=
for file in $managed_files; do
  if [ -e "$target_dir/$file" ]; then
    conflicts="${conflicts}
  - $file"
  fi
done

if [ -n "$conflicts" ]; then
  printf 'Error: target already contains managed workflow files:%s\n' "$conflicts" >&2
  printf 'Refusing to overwrite. Use this bootstrap only for a fresh agentic workspace.\n' >&2
  exit 1
fi

mkdir -p \
  "$target_dir/docs" \
  "$target_dir/works/templates" \
  "$target_dir/works/current" \
  "$target_dir/works/archives/backlogs" \
  "$target_dir/works/archives/work_items" \
  "$target_dir/scripts" \
  "$target_dir/.claude/commands" \
  "$target_dir/.claude/agents" \
  "$target_dir/.codex/agents"

cat > "$target_dir/AGENTS.md" <<'AGENTS_DOC'
# AGENTS.md

## Purpose

This repository defaults to agentic delivery via Claude Code or Codex. Both tools read this file. Use planning, tracked work items, and review gates for almost all coding work. Backlog-scheduled work uses the full phase/slice workflow; unrelated user requests may use the Standalone Work path below.

## Commit Convention

- Format: `type(scope): summary` — `scope` optional, imperative summary, no trailing period.
- Supported types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `revert`.
- Examples: `feat(api): add feedback capture endpoint`, `fix(storage): handle empty values`.

## Development Tooling

Follow the package manager, test commands, and build commands the repo already declares; do not introduce a second toolchain.

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

The full workflow is the default. A fast path is acceptable only for typo-only edits, one-line wording fixes, metadata-only changes, or tiny doc-only adjustments with no workflow impact. Never use the fast path when a change affects code behavior, tests, public contracts, architecture, repository workflow, or multiple files with nontrivial intent.

## Reference Doc Update Triggers

- `docs/product.md` — when goals, users, terminology, scope, or product direction change.
- `docs/architecture.md` — when component boundaries, data flow, storage shape, runtime choices, or repo structure change.
- `docs/api.md` — when a public contract is introduced, changed, stabilized, or deprecated.
- Record planned doc updates in `plan.md` and actual doc updates in `result.md` (or the final report for Standalone Work).

## Agent Tool Conventions

This workspace is dual-tool: both Claude Code and Codex read `AGENTS.md`.

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

- Codex reads `AGENTS.md` directly. Project-level slash commands do not exist in Codex; named workflows are user-home only (`~/.codex/prompts/` or skills).
- Subagents are configured under `.codex/agents/*.toml`. Each TOML file bridges to its canonical Markdown policy at `.claude/agents/<name>.md`. Edit the policy, not the bridge.
- Codex users invoke the workflow by reading the relevant `AGENTS.md` sections directly, or by wiring user-home skills that mirror the Claude Code slash commands.

## Reference Files

- `AGENTS.md` — canonical workflow rules (this file).
- `CLAUDE.md` — pointer to `AGENTS.md` so Claude Code finds the policy by its native default name.
- `docs/product.md` — problem, users, goals, terminology.
- `docs/architecture.md` — current repo shape and intended system design.
- `docs/api.md` — current and planned public contracts.
- `works/backlog.md` — actively scheduled phases and slices.
- `works/deferred.md` — parked jobs outside the active backlog.
- `works/templates/` — fresh templates for backlog, plan, and result.
- `.claude/commands/` — Claude Code slash commands.
- `.claude/agents/phase-reviewer.md` — phase-review gate policy.
- `.claude/agents/qa-agent.md` — mission-driven UI QA policy.
- `.codex/config.toml` — Codex project config.
- `.codex/agents/phase-reviewer.toml`, `.codex/agents/qa-agent.toml` — Codex bridges to the Markdown policies.
AGENTS_DOC

cat > "$target_dir/CLAUDE.md" <<'CLAUDE_POINTER'
# CLAUDE.md

Authority: see `/AGENTS.md`. Read it before any work in this repo.

The canonical workflow rules — phase/slice model, status, review gates, agent tool conventions — live in `AGENTS.md`. This file is a pointer so Claude Code finds the policy by its native default name.
CLAUDE_POINTER

cat > "$target_dir/docs/product.md" <<PRODUCT
# Product

## Status

$project_name is newly bootstrapped. Treat product scope, terminology, and public promises as draft until they are validated through the backlog workflow.

## Summary

$project_summary

## Target Users

- <primary user or customer>
- <secondary user or operator>

## Problem

- <problem this project solves>
- <current pain or workflow gap>

## Goals

- <goal>
- <goal>
- <goal>

## Non-Goals for Now

- <explicitly out-of-scope item>
- <explicitly out-of-scope item>

## Product Direction

- Keep this section current as product decisions are made.
- Move transient execution notes to \`works/\`; keep durable product truth here.

## Terminology

- \`phase\`: a grouped unit of work in \`works/backlog.md\`
- \`slice\`: a concrete step inside a phase
- \`work item\`: a timestamped execution folder under \`works/current/\` or \`works/archives/work_items/\`
PRODUCT

cat > "$target_dir/docs/architecture.md" <<ARCHITECTURE
# Architecture

## Status

$project_name is newly bootstrapped. This document should describe stable technical truth as the system takes shape.

## Current Repo Shape

- \`README.md\`: product-facing project overview
- \`AGENTS.md\`: canonical agentic workflow rules (read by Claude Code and Codex)
- \`CLAUDE.md\`: pointer to \`AGENTS.md\`
- \`docs/\`: stable reference documents
- \`works/\`: active backlog, deferred queue, active work items, archives, and templates
- \`scripts/\`: workflow helper scripts
- \`.claude/\`: Claude Code slash commands and subagents
- \`.codex/\`: Codex project config and agent bridges

## Intended System Shape

- <major component or runtime>
- <major component or runtime>
- <storage, external service, or integration if known>

## Runtime Shape

- <language, framework, or runtime>
- <entrypoint or service process>
- <local development command>
- <test command>

## Data and Storage

- <data model, storage engine, or persistence decision>
- <migration or compatibility constraints>

## Architecture Constraints

- Keep public contracts explicit in \`docs/api.md\`.
- Keep durable technical context here, not in transient work items.
- Keep execution history under \`works/\`.
- Keep currently scheduled work in \`works/backlog.md\` and intentionally deferred work in \`works/deferred.md\`.
- Prefer small slices and explicit review loops over large untracked changes.

## Open Questions

- <architecture question>
- <architecture question>
ARCHITECTURE

cat > "$target_dir/docs/api.md" <<'API_DOC'
# API

## Status

No public-facing contracts are finalized yet. Add contracts here when they are implemented or explicitly accepted.

## Purpose

Use this file to record public-facing contracts as they are implemented. Keep implementation notes out of this file unless they affect consumers.

## Documentation Rules

- Only document a contract as stable when it is implemented or explicitly accepted.
- Mark experimental surfaces as draft.
- Record breaking changes once external consumers exist.
- Keep public contract changes synchronized with `docs/product.md` and `docs/architecture.md` when product or system boundaries change.

## Contract Template

### Surface Name

- Status:
- Consumers:
- Purpose:
- Inputs:
- Outputs:
- Errors:
- Auth or permissions:
- Notes:

## Contracts

- None yet.
API_DOC

cat > "$target_dir/works/backlog.md" <<BACKLOG
# Backlog

## Status Model

- Phase: \`planned\`, \`in_progress\`, \`in_review\`, \`blocked\`, \`done\`
- Slice: \`todo\`, \`in_progress\`, \`in_review\`, \`changes_requested\`, \`done\`

## Usage Rules

- Every newly created phase starts with only \`decompose phase\` and \`phase review\`.
- Phase-level notes are allowed and encouraged; they do not count as slices.
- Do not pre-seed phase-specific middle slices in a newly created backlog.
- Add phase-specific middle slices only from the dedicated \`decompose phase\` slice.
- Keep \`phase review\` open until the phase passes review.
- If review fails, add dedicated fix slices and rerun review.
- Keep this file limited to actively scheduled phases and slices.
- This file schedules backlog-driven phases and slices only; unrelated standalone requests do not need phase, slice, or work-item entries.
- Move intentionally deferred work into \`works/deferred.md\` instead of leaving it in the active backlog.
- Link active work items from \`works/current/\`.
- If every documented phase is \`done\` and every documented slice is \`done\`, run \`scripts/rotate_backlog.sh\` (or \`/rotate-backlog\`) before starting new backlog-scheduled work.
- \`scripts/rotate_backlog.sh\` archives the active \`works/backlog.md\` file to \`works/archives/backlogs/<timestamp>_backlog.md\` and replaces it from \`works/templates/backlog.md\`.
- If the next request is standalone, completed-backlog rotation is housekeeping only and does not create a phase or slice for that request.
- Use stable phase IDs such as \`P1\`.
- Use stable slice IDs such as \`P1.DECOMP\`, \`P1.S1\`, \`P1.F1\`, and \`P1.REVIEW\`.
- Prefix each slice with \`[ ]\` until it is done, then switch it to \`[x]\`.
- Treat the checkbox as a visual summary only. The \`Status\` field remains authoritative.

## Active Phases

### Phase P1: $phase_name

- Phase ID: \`P1\`
- Objective: $phase_objective
- Status: planned
- Review outcome: pending
- Notes: Initial bootstrap phase. Use \`P1.DECOMP\` to create the concrete middle slices before implementation starts.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: \`P1.DECOMP\` | Name: \`decompose phase\` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: \`P1.REVIEW\` | Name: \`phase review\` | Status: todo | Work item: none | Notes: Run via the \`phase-reviewer\` subagent. Add fix slices if needed and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under \`works/archives/backlogs/\`.
- Archive completed work-item folders under \`works/archives/work_items/\`.
- Fresh backlog contents come from \`works/templates/backlog.md\`.
BACKLOG

cat > "$target_dir/works/deferred.md" <<'DEFERRED'
# Deferred Jobs

## Purpose

- Track work that is intentionally postponed outside the active execution order in `works/backlog.md`.
- Keep `works/backlog.md` focused on phases and slices that should drive `do the next slice` and `do the whole phase`.
- Promote deferred jobs back into `works/backlog.md` when they are ready to be scheduled.

## Usage Guide

- If the user asks to save tasks, follow-ups, later work, or ideas to `works/deferred.md`, add entries here immediately.
- A direct save-to-deferred request does not need a backlog phase, slice, or work-item folder.
- During slice implementation, add a deferred job when meaningful later work is discovered and it is not appropriate to add it to the current backlog as a slice, fix slice, or phase.
- Do not use this file for work required to complete the current slice or for issues required to make the current phase pass review. Those belong in the active work item or in review-driven fix slices.
- Deferred jobs do not affect current-phase selection. They become scheduled only after being promoted into `works/backlog.md`.

## Entry Rules

- Use stable deferred IDs such as `D1`, `D2`, or `D3`.
- Each deferred job should include a title, status, source, reason, and trigger for re-entry.
- Keep deferred jobs out of `works/backlog.md` until you actually want them to participate in active execution ordering.
- To add a job, scan existing `D*` entries and use the next unused number.
- Keep entries concise, actionable, and traceable to their source.
- If the source is a user request, write `Source: user request`.
- If the source is implementation work, write the phase/slice ID or work-item path when available.
- If the trigger is unknown, use `Trigger: user promotes or schedules this job`.

## Status Model

- `deferred`
- `ready`
- `done`
- `dropped`

## Deferred Jobs

- None yet.

## Entry Template

```md
### D<N>: <title>

- Deferred ID: `D<N>`
- Status: deferred
- Source: <user request | phase/slice/work item>
- Reason: <why this is parked instead of active backlog work>
- Trigger: <when to promote into works/backlog.md>
- Notes:
  - <optional concise context>
```
DEFERRED

cat > "$target_dir/works/templates/backlog.md" <<'BACKLOG_TEMPLATE'
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
- If every documented phase is `done` and every documented slice is `done`, run `scripts/rotate_backlog.sh` (or `/rotate-backlog`) before starting new backlog-scheduled work.
- `scripts/rotate_backlog.sh` archives the active `works/backlog.md` file to `works/archives/backlogs/<timestamp>_backlog.md` and replaces it from `works/templates/backlog.md`.
- If the next request is standalone, completed-backlog rotation is housekeeping only and does not create a phase or slice for that request.
- Use stable phase IDs such as `P1`.
- Use stable slice IDs such as `P1.DECOMP`, `P1.S1`, `P1.F1`, and `P1.REVIEW`.
- Prefix each slice with `[ ]` until it is done, then switch it to `[x]`.
- Treat the checkbox as a visual summary only. The `Status` field remains authoritative.

## Active Phases

### Phase P1: <phase name>

- Phase ID: `P1`
- Objective: <what this phase should accomplish>
- Status: planned
- Review outcome: pending
- Notes: <intent, constraints, assumptions, or handoff context>
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Run via the `phase-reviewer` subagent. Add fix slices if needed and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
- Fresh backlog contents come from `works/templates/backlog.md`.
BACKLOG_TEMPLATE

cat > "$target_dir/works/templates/plan.md" <<'PLAN_TEMPLATE'
# Plan

- Work item: __WORK_ITEM__
- Created at: __CREATED_AT__
- Phase ID: __PHASE_ID__
- Phase:
- Slice ID: __SLICE_ID__
- Slice:

## Goal

## Scope

## Context

## Milestones

1.
2.
3.
(more milestones available)..

## Validation

-

## Risks / open questions

-

## Docs to update

-
PLAN_TEMPLATE

cat > "$target_dir/works/templates/result.md" <<'RESULT_TEMPLATE'
# Result

- Work item: __WORK_ITEM__
- Created at: __CREATED_AT__
- Phase ID: __PHASE_ID__
- Phase:
- Slice ID: __SLICE_ID__
- Slice:
- Review status: pending
- Reviewer:
- Next action:

## Outcome

Summarize what shipped, or explain why the slice closed as `Blocked`.

## Deviations from plan

## Validation run

-

## Files changed

-

## Docs updated

-

## Roadmap updates

-

## Retrospective

-
RESULT_TEMPLATE

cat > "$target_dir/scripts/start_work.sh" <<'START_WORK'
#!/bin/sh
set -eu

usage() {
  printf 'Usage: %s <phase_id> <slice_id> <slug>\n' "$0" >&2
  exit 1
}

[ $# -eq 3 ] || usage

validate_id() {
  label=$1
  value=$2

  case "$value" in
    ''|*[!A-Za-z0-9._-]*)
      printf 'Error: %s must contain only letters, digits, dot, underscore, or hyphen.\n' "$label" >&2
      exit 1
      ;;
  esac
}

phase_id=$1
slice_id=$2
raw_slug=$3

validate_id "phase_id" "$phase_id"
validate_id "slice_id" "$slice_id"

slug=$(printf '%s' "$raw_slug" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '_' | sed 's/^_*//; s/_*$//')

if [ -z "$slug" ]; then
  printf 'Error: slug must contain at least one valid character.\n' >&2
  exit 1
fi

plan_template='works/templates/plan.md'
result_template='works/templates/result.md'

[ -f "$plan_template" ] || {
  printf 'Error: missing template %s\n' "$plan_template" >&2
  exit 1
}

[ -f "$result_template" ] || {
  printf 'Error: missing template %s\n' "$result_template" >&2
  exit 1
}

mkdir -p works/current

timestamp=$(date '+%Y%m%d_%H%M')
work_dir="works/current/${timestamp}_${slug}"

[ ! -e "$work_dir" ] || {
  printf 'Error: work item already exists at %s\n' "$work_dir" >&2
  exit 1
}

mkdir "$work_dir"

sed \
  -e "s|__WORK_ITEM__|$work_dir|g" \
  -e "s|__CREATED_AT__|$timestamp|g" \
  -e "s|__PHASE_ID__|$phase_id|g" \
  -e "s|__SLICE_ID__|$slice_id|g" \
  "$plan_template" > "$work_dir/plan.md"

sed \
  -e "s|__WORK_ITEM__|$work_dir|g" \
  -e "s|__CREATED_AT__|$timestamp|g" \
  -e "s|__PHASE_ID__|$phase_id|g" \
  -e "s|__SLICE_ID__|$slice_id|g" \
  "$result_template" > "$work_dir/result.md"

printf '%s\n' "$work_dir"
START_WORK

cat > "$target_dir/scripts/archive_work.sh" <<'ARCHIVE_WORK'
#!/bin/sh
set -eu

usage() {
  printf 'Usage: %s <work_dir_name>\n' "$0" >&2
  exit 1
}

[ $# -eq 1 ] || usage

case "$1" in
  */*)
    printf 'Error: pass a work directory name, not a path.\n' >&2
    exit 1
    ;;
esac

name=$1
src="works/current/$name"
dst="works/archives/work_items/$name"

[ -d "$src" ] || {
  printf 'Error: work item not found at %s\n' "$src" >&2
  exit 1
}

mkdir -p works/archives/work_items

[ ! -e "$dst" ] || {
  printf 'Error: archive destination already exists at %s\n' "$dst" >&2
  exit 1
}

mv "$src" "$dst"

printf '%s\n' "$dst"
ARCHIVE_WORK

cat > "$target_dir/scripts/rotate_backlog.sh" <<'ROTATE_BACKLOG'
#!/bin/sh
set -eu

if [ $# -ne 0 ]; then
  printf 'Usage: %s\n' "$0" >&2
  exit 1
fi

template='works/templates/backlog.md'
current='works/backlog.md'
archive_dir='works/archives/backlogs'

[ -f "$template" ] || {
  printf 'Error: missing template %s\n' "$template" >&2
  exit 1
}

[ -f "$current" ] || {
  printf 'Error: backlog not found at %s\n' "$current" >&2
  exit 1
}

mkdir -p "$archive_dir"

timestamp=$(date '+%Y%m%d_%H%M')
archive="$archive_dir/${timestamp}_backlog.md"

[ ! -e "$archive" ] || {
  printf 'Error: archive path already exists at %s\n' "$archive" >&2
  exit 1
}

mv "$current" "$archive"
cp "$template" "$current"

printf 'archived: %s\n' "$archive"
printf 'fresh: %s\n' "$current"
ROTATE_BACKLOG

cat > "$target_dir/.claude/commands/do-next-slice.md" <<'DO_NEXT_SLICE'
---
description: Continue the current backlog phase one slice at a time (backlog-driven).
---

Read AGENTS.md, works/backlog.md, works/deferred.md, and any in-progress folders under works/current/. Follow the "Execution Commands" rules in AGENTS.md.

Resolve the current phase: scan works/backlog.md top-to-bottom and pick the first phase whose status is not `done`. If that phase is `blocked`, surface the blocker and stop.

Resolve the next slice: the first slice in the current phase whose status is not `done`. Do not skip fix slices or `phase review` slices.

If the next slice is `phase review`, invoke the `phase-reviewer` subagent (Agent tool, subagent_type: phase-reviewer) and apply its verdict per AGENTS.md.

Otherwise: if a matching active work item already exists under works/current/, continue it. If not, run `scripts/start_work.sh <phase_id> <slice_id> <slug>` to create one. Fill plan.md before code changes, implement, then fill result.md.

Stop after one slice. Do not advance to the next slice in the same turn.
DO_NEXT_SLICE

cat > "$target_dir/.claude/commands/do-whole-phase.md" <<'DO_WHOLE_PHASE'
---
description: Finish the current backlog phase end-to-end, including phase review and any fix slices.
---

Read AGENTS.md and works/backlog.md. Resolve the current phase per the "Execution Commands" rules in AGENTS.md. Work through every remaining slice in that phase in order until the phase is `done`, `blocked`, or paused for user input.

Stay within the current phase. Do not advance into later phases.

When you reach `phase review`, invoke the `phase-reviewer` subagent (Agent tool, subagent_type: phase-reviewer). If review returns `changes_requested`, add the proposed fix slices to works/backlog.md, complete them, then rerun review. Repeat until review passes or the phase becomes blocked.

A `do the whole phase` command may create one work item per slice as needed. The initial coordination work item (if any) stays open until all slice work items it initiated are complete; record the phase-level result last.

## Fallback if `phase-reviewer` isn't registered

Claude Code scans `.claude/agents/` at session start. If your current session was started before `.claude/agents/phase-reviewer.md` existed, or if the agent file is otherwise not discoverable, the Agent tool call will fail with "Agent type 'phase-reviewer' not found". A full Claude Code restart usually fixes it; until then, use this fallback so the phase still closes cleanly:

1. `Read` `.claude/agents/phase-reviewer.md` and strip its YAML frontmatter (the block between the two `---` markers and the markers themselves).
2. Invoke the Agent tool with `subagent_type: general-purpose`. The prompt opens with the verbatim phase-reviewer policy body, then continues with the standard phase-review brief: the phase ID and objective, the slice list with statuses, the work-item folders to read (`works/current/...` and `works/archives/work_items/...` that belong to the phase), and an explicit instruction to emit one of `pass | changes_requested | blocked` per the policy.
3. Apply the verdict the same way as a native `phase-reviewer` call: record it in the phase review work item, update `works/backlog.md`, and add explicit fix slices (`P<N>.F<n>`) if the verdict is `changes_requested`.

The fallback agent is read-only — same contract as the native subagent. The calling Claude is still the one that applies the verdict.
DO_WHOLE_PHASE

cat > "$target_dir/.claude/commands/start-work.md" <<'START_WORK_CMD'
---
description: Create a timestamped work-item folder under works/current/ via scripts/start_work.sh.
argument-hint: <phase_id> <slice_id> <slug>
allowed-tools: Bash(scripts/start_work.sh:*)
---

Run `scripts/start_work.sh $ARGUMENTS` to create a new work item from the templates in works/templates/. Report the resulting path.
START_WORK_CMD

cat > "$target_dir/.claude/commands/archive-work.md" <<'ARCHIVE_WORK_CMD'
---
description: Archive a completed work item from works/current/ to works/archives/work_items/.
argument-hint: <work_dir_name>
allowed-tools: Bash(scripts/archive_work.sh:*)
---

Run `scripts/archive_work.sh $ARGUMENTS`. Pass the work directory **name only**, not a path. Report the archive destination.
ARCHIVE_WORK_CMD

cat > "$target_dir/.claude/commands/rotate-backlog.md" <<'ROTATE_BACKLOG_CMD'
---
description: Archive the active backlog and replace it with the fresh template (run only when every phase and slice is done).
allowed-tools: Bash(scripts/rotate_backlog.sh:*)
---

Verify works/backlog.md shows every phase as `done` and every slice as `done`, then run `scripts/rotate_backlog.sh`. Report both the archive path and the new backlog path.
ROTATE_BACKLOG_CMD

cat > "$target_dir/.claude/commands/commit.md" <<'COMMIT_CMD'
---
description: Group pending changes by topic and create one focused commit per group, following the project's commit convention.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git reset:*), Bash(git restore:*), Bash(git commit:*)
---

Group the current pending changes into topic-focused commits, then create one commit per group following the `type(scope): summary` convention from AGENTS.md.

Steps:

1. Inspect repo state in parallel:
   - `git status` (no `-uall`) to see tracked and untracked files.
   - `git diff` and `git diff --staged` to see all pending content.
   - `git log -n 10 --oneline` to match this repo's commit style.

2. Read the actual diffs of changed files so you understand intent before grouping. Group by **topic / logical change**, not by directory — one feature, one bug fix, one doc update, one refactor. Files that share intent go together even if they live in different folders.

3. Skip files that look sensitive (e.g. `.env`, credentials, large binaries). If staged accidentally, leave them out and warn the user at the end.

4. For each group, in order:
   - Reset the index (`git reset` with no args) so only this group's files are staged.
   - Stage that group's files explicitly by path. Never use `git add -A` or `git add .`.
   - Draft a `type(scope): summary` message using imperative voice, no trailing period, focused on **why** when non-obvious. Supported types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `revert`.
   - Commit using a HEREDOC so the message formats correctly. End with a `Co-Authored-By:` trailer naming the assisting agent if the user wants attribution; otherwise omit.
   - If a pre-commit hook fails: do **not** `--amend`. Fix the underlying issue, re-stage, create a **new** commit for that group.

5. After all groups are committed, run `git status` once more to confirm a clean tree (or to surface anything intentionally left unstaged).

6. Report the resulting commits as a short list: `<short-sha> <message>` per line, plus any files you deliberately did not commit and why.

Rules:

- Never push. Never force-push. Never run destructive git commands (`reset --hard`, `clean -f`, `checkout .`) to "tidy up" before committing — preserve all user changes.
- Never skip hooks (`--no-verify`) or signing flags unless the user explicitly asks.
- Never amend an existing commit unless the user explicitly asks.
- Do not create empty commits. Drop groups that end up empty after filtering.
- If everything is one cohesive change, a single commit is fine — don't fabricate splits.
- If grouping is genuinely ambiguous, ask the user once before committing.
COMMIT_CMD

cat > "$target_dir/.claude/commands/qa-check.md" <<'QA_CHECK_CMD'
---
description: Run the QA agent against a mission brief (or the full mission library).
---

Run the QA agent for the user's argument. The QA agent lives at `.claude/agents/qa-agent.md` and is invoked via the `Agent` tool with `subagent_type: qa-agent`. It mirrors `phase-reviewer`'s verdict shape (`pass | changes_requested | blocked`) and writes evidence into the supplied artifact directory.

## Argument modes

- `/qa-check` (no arg) — run every mission in your project's mission library sequentially.
- `/qa-check <mission_id>` — run a single mission by id (matches the file name under your project's mission library).
- `/qa-check <inline brief>` — run an ad-hoc mission described inline. The argument is treated as the mission body Markdown.

## Per-mission orchestration

For each mission:

1. Resolve the mission body (file path or inline string) and confirm the project's QA driver is up and pointing at the deployed code path. If the driver is not running, surface the error and stop.
2. Create an artifact directory under the active work item (e.g. `works/current/<work>/browser/qa-<mission_id>-<run>/`) where the agent will write `transcript.md` and `summary.json`.
3. Invoke the QA agent via the `Agent` tool with `subagent_type: qa-agent`. Pass the mission body, the artifact directory, the driver's send command/socket, and the turn budget.
4. Wait for the subagent to finish.
5. Tear down the driver session.
6. Read `<artifact_dir>/summary.json` and print the verdict plus a one-line summary back to the user. If `verdict === "changes_requested"`, list the proposed fix slices.

## Multi-mission aggregation (no-arg invocation)

- Run missions sequentially (one driver/browser at a time).
- After all missions finish, print a brief table: `mission_id`, `verdict`, finding count, artifact dir.
- If any mission's verdict is `failure` or `blocked`, the overall result is `changes_requested`; otherwise `pass`.

## Wiring this up

This bootstrap ships the QA *policy* (`.claude/agents/qa-agent.md`) and the *invocation contract* (this file). The browser/UI driver, mission library, and artifact pipeline are project-defined — wire them up under `scripts/qa-agent/` (or wherever fits your repo) before `/qa-check` will do useful work. The driver only needs to expose the capability surface listed under "Driver assumption" in `.claude/agents/qa-agent.md`.

## Fallback if `qa-agent` isn't registered

Claude Code scans `.claude/agents/` at session start. If your session was started before `.claude/agents/qa-agent.md` existed, the Agent call in step 3 above will fail with "Agent type 'qa-agent' not found". A full Claude Code restart usually fixes it; until then:

1. `Read` `.claude/agents/qa-agent.md` and strip its YAML frontmatter.
2. In step 3, invoke the Agent tool with `subagent_type: general-purpose`. The prompt opens with the verbatim qa-agent policy body, then continues with the mission body, driver send command, socket path, artifact directory, and turn budget exactly as the native invocation requires.
3. Apply the verdict the same way as a native `qa-agent` call: read `summary.json` from the artifact directory, tear down the driver, surface the verdict.

The fallback agent has the same contract as the native subagent — it only writes `transcript.md` and `summary.json` and emits the verdict line.
QA_CHECK_CMD

cat > "$target_dir/.claude/agents/phase-reviewer.md" <<'PHASE_REVIEWER'
---
name: phase-reviewer
description: Reviews a completed backlog phase against its objective and slices. Returns pass / changes_requested / blocked. Read-only — caller applies the verdict.
tools: Read, Glob, Grep, Bash
---

You are the phase reviewer for a backlog-driven agentic workspace defined in AGENTS.md.

What to read:

- AGENTS.md (workflow rules)
- docs/product.md, docs/architecture.md, docs/api.md (reference truth)
- works/backlog.md (current phase, objective, slice list, statuses, notes)
- result.md from each completed work item under works/current/ and works/archives/work_items/ that belongs to the phase under review

What to check:

- Does the phase objective hold up against what shipped?
- Did each slice meet its plan? Are deviations explained in result.md?
- Were the right reference docs (docs/product.md, docs/architecture.md, docs/api.md) updated when triggers in AGENTS.md fired?
- Were validation runs recorded?
- Are there gaps that warrant explicit fix slices before closing the phase?

Output exactly one of:

- `pass` — with a short justification.
- `changes_requested` — with a numbered list of issues. For each issue propose a fix slice: ID like `P<N>.F<N>`, name, one-line scope.
- `blocked` — with what is blocking and what input is needed.

Do not edit files. The calling agent applies your verdict (updates backlog.md, creates fix slices, etc.).

## Optional: invoke the QA agent when the phase touches UI

If the phase under review changed any of:

- any UI-facing route or component
- any chat/stream/SSE contract that a browser consumes
- any public-facing API surface visible to browsers

then invoke the `qa-agent` subagent (Agent tool, subagent_type: `qa-agent`) against one or more relevant missions before finalizing your verdict. Either pick a library mission whose scope matches what the phase touched (see your project's QA driver setup), or compose a short inline mission brief naming the routes/components the phase touched and the "what would feel wrong" criteria you'd test for if you were a user.

QA findings flow into your verdict:

- Any `failure`-severity finding → `changes_requested` with a corresponding fix slice.
- Any `warning`-severity finding → consider it; if it's a real regression worth fixing, add to the fix-slice list. If it's a known-benign artifact, note it in your justification but do not block on it.
- `info`-severity findings are informational only.

You remain the single verdict authority. The QA agent's `summary.json` is evidence; your verdict line is the decision.

If the QA driver is unreachable from the review environment, continue with the normal docs+slices review and note in your justification that QA evidence was not collected. Do not mark the phase `blocked` solely on QA-environment availability.
PHASE_REVIEWER

cat > "$target_dir/.claude/agents/qa-agent.md" <<'QA_AGENT'
---
name: qa-agent
description: Drives a project-defined browser/UI driver against a free-form mission brief like a curious human tester. Records continuously, drops into inspection mode when something looks off, and emits pass / changes_requested / blocked mirroring phase-reviewer. Read-only — caller applies the verdict.
tools: Bash, Read, Glob, Grep, Write
---

You are the QA agent. The calling agent or the `/qa-check` slash command hands you a mission and an artifact directory. You drive the project's UI/browser driver turn-by-turn, behave like a real user pushing on the product, and emit a verdict.

You are **not a scripted test runner**. Mission briefs are prompts, not test cases. There are no fixed step sequences, no expected DOM trees, no assertion blocks. Your job is to notice "this feels off" things a deterministic spec would miss — sub-second flickers, awkward layouts, surprising loading states, broken UX — and escalate them with evidence.

## Driver assumption

The project supplies a driver exposing at minimum these verbs (exact command names vary by project):

- `observe` — current interactive elements, viewport, fresh screenshot reference.
- `screenshot` — capture a single shot to disk.
- `click`, `type`, `keyboard`, `wait_for_selector`, `wait_for_ms`, `goto` — interaction primitives.
- `console_tail`, `network_tail` — recent browser console / network entries.
- `inspect_dom` — live DOM dump for a selector.
- `mutation_window` — recorded DOM mutations in a time window.
- `stop` — end the recording and freeze the trace.

The rest of this file references the driver generically (`driver observe`, `driver screenshot`, etc.).

## What you receive

The calling agent gives you:

1. **Mission** — either a `mission_id` resolving to a file under your project's mission library, or an inline Markdown brief in the same format. Read the entire brief body.
2. **Artifact directory** (absolute path) — you write `transcript.md` and `summary.json` here at the end.
3. **Driver send command** — how to invoke the driver (project-defined; commonly a `bash send.sh <cmd> '<json-args>'` wrapper or equivalent).
4. **Turn budget** — soft cap means "wrap up exploration"; hard cap means "emit the verdict even if `blocked` is the answer".

## Per-turn loop

`observe → decide → act → observe`. Each iteration: call `driver observe`, compare against the mission's "What a real user would try" section, pick the next thing a curious tester would do (or drop into inspection mode if something already looks off), call the appropriate driver command, then observe again to confirm the act had the expected effect.

## Inspection mode

Drop into inspection when any of these are true:

- `observe` shows an element you expected, missing — or vice versa.
- A click "worked" visually but `network_tail` shows the expected outgoing request never fired.
- The screen visibly flashed (use `mutation_window` plus any post-stop frame/trace tools to confirm).
- A heuristic flicker pass (if the driver provides one) flagged activity near an action you just took.

Use `mutation_window`, `inspect_dom`, and any post-stop frame/trace tools the driver exposes. Treat detector outputs as **investigation hints**, not verdicts.

## Severity discipline

- **`failure`** — you would not ship this. Concrete user-visible breakage.
- **`warning`** — you noticed it; a real user would notice it; you can describe it precisely with evidence. Sub-second flickers on busy/disabled state are warning-grade by default.
- **`info`** — you noticed it but you're not sure. Aesthetic nits, one-off blips that don't reproduce, benign-looking detector hits.

When in doubt, mark `info`. Findings stack; the verdict aggregates them — better ten honest infos than one shaky failure. The LLM owns the verdict; the detector does not.

## Verdict

Mirror `phase-reviewer.md` exactly. Emit one of:

- **`pass`** — short justification.
- **`changes_requested`** — numbered findings. For each, propose a fix slice: ID `P<N>.F<n>`, name, one-line scope.
- **`blocked`** — what is blocking and what input you need. Common reasons: driver unreachable, turn budget exhausted before reaching the mission's core path, mission ambiguous.

The verdict is your final user-facing output. Put it last.

## Output discipline

Before emitting the verdict, persist two files in the artifact directory.

### `transcript.md`

Human-readable log of what you did. Loose Markdown; one section per major decision (`### Turn 1 — observe landing`, `### Turn 7 — clicked thumbs-up, noticed status flicker`, etc.). Future operators read this to understand why you flagged what you flagged.

### `summary.json`

Machine-readable for the orchestrator and the reviewer integration. Use this schema:

```json
{
  "mission_id": "<id>",
  "verdict": "pass | changes_requested | blocked",
  "summary": "<one-line>",
  "turn_count": 0,
  "turn_budget": 0,
  "started_at_ms": 0,
  "ended_at_ms": 0,
  "artifact_dir": "<abs path>",
  "findings": [
    {
      "id": "F1",
      "severity": "info | warning | failure",
      "title": "<short>",
      "description": "<what, with evidence cited>",
      "evidence": {
        "action_ids": [],
        "frames": [],
        "mutation_window": { "start_ms": 0, "end_ms": 0 },
        "trace_snippet": { "action_id": 0 }
      },
      "proposed_fix_slice": {
        "id": "P<N>.F<n>",
        "name": "<short>",
        "scope_one_line": "<what to change>"
      }
    }
  ],
  "stack_health": {
    "checked": true,
    "verified_deployed_code": true,
    "notes": "<one-line driver/stack status>"
  }
}
```

Schema rules:

- `verdict` ∈ `pass | changes_requested | blocked`.
- `findings[].severity` ∈ `info | warning | failure`.
- `findings[].evidence` always present; at minimum list the `action_ids` you used.
- `findings[].proposed_fix_slice` required only when `verdict === "changes_requested"`.
- The orchestrator may extend the JSON with additional fields (e.g. `run_id`, `git_sha`). Treat your output as a partial.

After writing both files, end your response with the verdict line plus a short justification. The calling agent applies the verdict.

## Boundary

You may only `Write` `transcript.md` and `summary.json` inside the supplied artifact directory. Do not edit application files, documentation, backlog files, mission briefs, or workflow files.
QA_AGENT

cat > "$target_dir/.codex/config.toml" <<'CODEX_CONFIG'
# Keep this minimal at first.
# Add project-specific Codex settings here only after you notice repeated friction.
CODEX_CONFIG

cat > "$target_dir/.codex/agents/phase-reviewer.toml" <<'PHASE_REVIEWER_CODEX'
name = "phase-reviewer"
description = "Reviews a completed backlog phase against its objective and slices. Returns pass, changes_requested, or blocked without editing files."
sandbox_mode = "read-only"

developer_instructions = """
You are the Codex adapter for this workspace's canonical phase-review subagent.

Before taking any action, read `.claude/agents/phase-reviewer.md`. Ignore only
its YAML frontmatter and apply its Markdown policy body as your primary
instructions. Preserve its reading list, review criteria, verdict shape
(pass / changes_requested / blocked), and the optional QA-agent escalation
path.

Apply these platform translations only:
- References to the calling Claude mean the parent Codex agent.
- Use Codex shell and file tools in place of Claude tool names.

You are read-only. Do not edit application files, documentation, backlog
files, or workflow files. The parent agent applies your verdict.
"""
PHASE_REVIEWER_CODEX

cat > "$target_dir/.codex/agents/qa-agent.toml" <<'QA_AGENT_CODEX'
name = "qa-agent"
description = "Drives the project's UI/browser driver through mission-driven QA runs like a curious user, records evidence, and emits pass, changes_requested, or blocked without changing application code."
sandbox_mode = "workspace-write"

developer_instructions = """
You are the Codex adapter for this workspace's canonical mission-driven QA agent.

Before taking any QA action, read `.claude/agents/qa-agent.md`. Ignore only
its YAML frontmatter and apply its Markdown policy body as your primary
instructions. Preserve its driver assumption, mission loop, inspection
behavior, severity discipline, output schema, and verdict contract.

Apply these platform translations only:
- References to the calling Claude or `/qa-check` mean the parent Codex agent
  or a Codex skill that wraps the same workflow.
- Use Codex shell and file tools in place of Claude tool names.
- Resolve any `[[name]]` cross-references from your project's own
  memory/notes location.

The parent gives you the mission body, driver send command, artifact
directory, and turn budget. Drive the existing driver; do not reimplement
orchestration. You may write only `transcript.md` and `summary.json`
inside the supplied artifact directory. Do not edit application files,
documentation, backlog files, configuration, mission briefs, or workflow
files. Report fixes as proposed fix slices only.
"""
QA_AGENT_CODEX

chmod +x \
  "$target_dir/scripts/start_work.sh" \
  "$target_dir/scripts/archive_work.sh" \
  "$target_dir/scripts/rotate_backlog.sh"

printf 'Bootstrapped agentic workspace at %s\n' "$target_dir"
printf 'Canonical workflow doc: AGENTS.md (read by Claude Code and Codex). CLAUDE.md is a pointer.\n'
printf 'Created initial phase: P1 - %s\n' "$phase_name"
printf 'Slash commands registered: /do-next-slice, /do-whole-phase, /start-work, /archive-work, /rotate-backlog, /commit, /qa-check\n'
printf 'Subagents registered: phase-reviewer, qa-agent (Claude Code Markdown + Codex TOML bridges)\n'
printf 'Next backlog command: /do-next-slice (or magic phrase: do the next slice)\n'
