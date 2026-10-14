---
name: doc-new-version
description: Create a new versioned durable doc instead of patching current docs.
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit
disable-model-invocation: true
---

# doc-new-version

Run `python3 scripts/workflow.py doc-new-version $ARGUMENTS` (for example `--doc product --summary "..." --source P1.S1`).

**Where this belongs:** in a **docs phase** — the operator-created phase that consolidates the `## Doc impact` notes earlier phases left behind (`python3 scripts/workflow.py docs-debt` prints exactly which notes those are; the `create-phase` skill's *docs-phase route* starts the phase) — and on the **default stream** (versions come from one shared index). Not in an ordinary slice, and not at a phase review beyond its two named gate sections (`## Regression Checklist`, `## Operator Runtime`). When a phase's notes are all consolidated, record it: `python3 scripts/workflow.py docs-consolidated <P>`.

Then edit only the returned `edit_path` under `docs/versions/<doc>/`, and run:

```sh
python3 scripts/workflow.py rebuild-docs
python3 scripts/workflow.py validate
```

**If the command prints an `oversized_doc_sections=` note** (the same text `validate` warns with), split the section(s) it names *in this version file* — a section past the threshold has outgrown the read-order rule, so "read only the sections the work touches" has quietly become "read the doc". Splitting is per-doc judgment while you are already editing that doc, never a sweep across the doc set: a small doc whose few sections are its whole content is measurably better left exactly as it is.

Never manually edit `docs/current/*.md` or any existing file under `docs/versions/`.
