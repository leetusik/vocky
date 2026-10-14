---
name: executor-route
description: Show the executor route table (model and effort per route, the per-row executors.toml overrides, the agent files' sync state) and the dispatch record's summary; with a slice id, the dispatch decision for that slice.
argument-hint: "[<slice_id> [--retry] | --drafter | --explore]"
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# executor-route

The engine owns one executor route table: each row (`high`, `research`, `mid`, `cheap`, `explore`) names the agent file it dispatches and the model and effort passed on the Agent call. An unset `cheap` row inherits the `mid` row; a per-row `[claude.<row>]` block in the repo-root `executors.toml` overrides the engine default, and `python3 scripts/workflow.py sync-agents` writes it into the agent files' frontmatter (the fallback when no per-dispatch value is passed). There are no presets.

Run `python3 scripts/workflow.py executor-route $ARGUMENTS` and relay its output:

- **No argument: the table.** It prints every row's tier, model, effort and source (`default`, `executors.toml`, `mid row`), whether the agent files are in sync with it, and the proxy line. Then also run `python3 scripts/workflow.py dispatch-summary` and relay it: the recorded executor runs by route, by model @ effort and by kind — the evidence the table is tuned from.
- **A slice id (`--retry` for a second attempt): the decision.** It prints the slice's route, the reason, the agent (`subagent_type=`), the model and effort with whether each is passed on the Agent call (`pass_model=`, `pass_effort=`), and the commit attribution. These are the lines the orchestrator pins as the slice's `## Dispatch` section.
- **`--drafter` / `--explore`:** the same lines for the `design-drafter` span and for read-only `Explore` lookups.

Relay any `fallback=` line (a loopback proxy moved a row to another model; `model=` already carries it) and any `warning=` line (an environment variable will override the per-dispatch value on this machine) as-is.

The skill edits nothing and commits nothing. To change a row, the operator edits its `[claude.<row>]` block in `executors.toml` and runs `sync-agents`; never edit their overrides on your own.
