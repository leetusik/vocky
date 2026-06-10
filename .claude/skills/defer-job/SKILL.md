---
name: defer-job
description: Park work as a deferred job folder, outside active backlog selection.
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# defer-job

Run `python3 scripts/workflow.py defer-job $ARGUMENTS` (for example `--title "..." --reason "..." --trigger "..." --source P1.S1`).

Deferred jobs are stored under `works/deferred/open/<DID>/` and never affect next-slice selection until promoted.
