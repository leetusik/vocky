# P1.F1 — Restore REST target_type help string in docs.json

> Native plan for slice **P1.F1** (`fix`, risk **low** → `slice-executor-low`, a literal
> plan-follower). Exact edit below — apply verbatim, no judgment. You never commit and never
> transition slice/phase status; write `result.md`, append a one-line note to `phase.md`, and
> return your verdict. If anything differs from what's described, **escalate** rather than guess.

## Context

P1.REVIEW found one regression: `make verify`'s `package-check` step fails. The packaging validator
`scripts/check_admin_ui_package.py` (lines 108–119) requires the exact substring
`target_type message, conversation, or surface` to be present in the packaged admin help asset
`src/vocky/admin_assets/docs.json`. S2's MCP scrub of `docs.json` removed that REST/admin string
(it sat next to a removed MCP bullet). `make test` (132 passed) and `make smoke` are green — only
the packaging validator is red. This slice re-adds the string in a REST/admin-appropriate,
MCP-free spot.

## Edit (exact) — `src/vocky/admin_assets/docs.json`

In the `admin-rest` topic's `"type": "list"` block, add one new bullet immediately after the
existing "Admin UI target type filter" bullet. Replace this exact two-line span:

```
                "The Admin UI target type filter uses Any, message, conversation, and surface. Any leaves older records with unset target_type visible; there is no dedicated unset target_type filter.",
                "source_metadata and attributes are visible as read-only JSON in the Admin UI even though Admin REST can patch them.",
```

with:

```
                "The Admin UI target type filter uses Any, message, conversation, and surface. Any leaves older records with unset target_type visible; there is no dedicated unset target_type filter.",
                "Filter by target_type message, conversation, or surface to review message, conversation, and product-surface feedback separately.",
                "source_metadata and attributes are visible as read-only JSON in the Admin UI even though Admin REST can patch them.",
```

The only change is the inserted new bullet line (with its trailing comma). Do **not** change any
other line, the `topic_ids`, or the `rest_capture_try` block. Do **not** reintroduce any MCP wording
(no `list_feedback` / `summarize_feedback` / `/mcp`).

## Verification
- `python3 -c "import json; json.load(open('src/vocky/admin_assets/docs.json'))"` → no error (valid JSON).
- `grep -c "target_type message, conversation, or surface" src/vocky/admin_assets/docs.json` → `1`.
- `grep -c "\bmcp\b\|/mcp\|list_feedback\|summarize_feedback" src/vocky/admin_assets/docs.json` → `0`.
- Full green: if the compose stack is up (the review ran `make bootstrap`), run `make verify` — it
  must now pass fully (package-check + smoke + test). If the stack is down, run `make bootstrap`
  first, then `make verify`. If `make verify` does not report success for any reason other than a
  clean pass, **escalate** with the output (do not claim green).

## phase.md note (append when done)
One line under Findings & Notes, e.g. "P1.F1 done: restored the required REST help string
'target_type message, conversation, or surface' to docs.json admin-rest block; make verify green."
