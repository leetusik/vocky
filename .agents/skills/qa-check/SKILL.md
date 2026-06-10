---
name: qa-check
description: Run the QA agent against a mission brief (or the full mission library).
---

# qa-check

Run the QA agent for the operator's argument. The QA agent policy lives at `.claude/agents/qa-agent.md`; the Codex bridge is `.codex/agents/qa-agent.toml`. It mirrors `phase-reviewer`'s verdict shape (`pass | changes_requested | blocked`) and writes evidence into the supplied artifact directory.

## Argument modes

- no arg — run every mission in your project's mission library sequentially.
- `<mission_id>` — run a single mission by id (matches the file name under your project's mission library).
- `<inline brief>` — run an ad-hoc mission described inline. The argument is treated as the mission body Markdown.

## Per-mission orchestration

For each mission:

1. Resolve the mission body (file path or inline string) and confirm the project's QA driver is up and pointing at the deployed code path. If the driver is not running, surface the error and stop.
2. Create an artifact directory under the active slice folder (e.g. `works/phases/active/<P>/slices/<slice_id>/browser/qa-<mission_id>-<run>/`) for `transcript.md` and `summary.json`. If no slice is active, use a scratch path such as `works/qa/qa-<mission_id>-<run>/`.
3. Drive the QA agent via the Codex qa-agent bridge (`.codex/agents/qa-agent.toml`). Pass the mission body, the artifact directory, the driver's send command/socket, and the turn budget.
4. Wait for the agent to finish, then tear down the driver session.
5. Read `<artifact_dir>/summary.json` and print the verdict plus a one-line summary. If the verdict is `changes_requested`, list the proposed fix slices.

## Multi-mission aggregation (no-arg invocation)

- Run missions sequentially (one driver/browser at a time).
- After all missions finish, print a brief table: `mission_id`, `verdict`, finding count, artifact dir.
- If any mission's verdict is `failure` or `blocked`, the overall result is `changes_requested`; otherwise `pass`.

## Wiring this up

This workspace ships the QA *policy* (`.claude/agents/qa-agent.md`) and this *invocation contract*. The browser/UI driver, mission library, and artifact pipeline are project-defined — wire them up under `scripts/qa-agent/` (or wherever fits your repo) before this skill does useful work. The driver only needs to expose the capability surface listed under "Driver assumption" in `.claude/agents/qa-agent.md`.
