---
description: Finish the current backlog phase end-to-end, including phase review and any fix slices.
---

Read CLAUDE.md and works/backlog.md. Resolve the current phase per the "Execution Commands" rules in CLAUDE.md. Work through every remaining slice in that phase in order until the phase is `done`, `blocked`, or paused for user input.

Stay within the current phase. Do not advance into later phases.

When you reach `phase review`, invoke the `phase-reviewer` subagent (Agent tool, subagent_type: phase-reviewer). If review returns `changes_requested`, add the proposed fix slices to works/backlog.md, complete them, then rerun review. Repeat until review passes or the phase becomes blocked.

A `do the whole phase` command may create one work item per slice as needed. The initial coordination work item (if any) stays open until all slice work items it initiated are complete; record the phase-level result last.

## Fallback if `phase-reviewer` isn't registered

Claude Code scans `.claude/agents/` at session start. If your current session was started before `.claude/agents/phase-reviewer.md` existed, or if the agent file is otherwise not discoverable, the Agent tool call will fail with "Agent type 'phase-reviewer' not found". A full Claude Code restart usually fixes it; until then, use this fallback so the phase still closes cleanly:

1. `Read` `.claude/agents/phase-reviewer.md` and strip its YAML frontmatter (the block between the two `---` markers and the markers themselves).
2. Invoke the Agent tool with `subagent_type: general-purpose`. The prompt opens with the verbatim phase-reviewer policy body, then continues with the standard phase-review brief: the phase ID and objective, the slice list with statuses, the work-item folders to read (`works/current/...` and `works/archives/work_items/...` that belong to the phase), and an explicit instruction to emit one of `pass | changes_requested | blocked` per the policy.
3. Apply the verdict the same way as a native `phase-reviewer` call: record it in the phase review work item, update `works/backlog.md`, and add explicit fix slices (`P<N>.F<n>`) if the verdict is `changes_requested`.

The fallback agent is read-only — same contract as the native subagent. The calling Claude is still the one that applies the verdict.
