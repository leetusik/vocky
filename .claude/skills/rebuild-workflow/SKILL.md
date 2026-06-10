---
name: rebuild-workflow
description: Rebuild generated workflow dashboards, indexes, and docs snapshots, then validate.
allowed-tools: Bash(python3 scripts/workflow.py:*)
disable-model-invocation: true
---

# rebuild-workflow

Run:

```sh
python3 scripts/workflow.py rebuild
python3 scripts/workflow.py validate
```
