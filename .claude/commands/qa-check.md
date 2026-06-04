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
