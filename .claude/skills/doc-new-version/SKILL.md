---
name: doc-new-version
description: Create a new versioned durable doc instead of patching current docs.
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit
disable-model-invocation: true
---

# doc-new-version

Run `python3 scripts/workflow.py doc-new-version $ARGUMENTS` (for example `--doc product --summary "..." --source P1.S1`).

Then edit only the returned `edit_path` under `docs/versions/<doc>/`, and run:

```sh
python3 scripts/workflow.py rebuild-docs
python3 scripts/workflow.py validate
```

Never manually edit `docs/current/*.md` or any existing file under `docs/versions/`.
