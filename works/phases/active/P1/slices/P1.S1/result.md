# P1.S1 — Result

Executed the plan literally: three declaration-file edits, no code or durable-doc changes.

## Changes

1. `LICENSE` — full-file replace: the ~660-line AGPL-3.0 text is gone; the file now contains
   exactly the MIT text from the plan, copyright `Copyright (c) 2026 Vocky`.
2. `pyproject.toml:11` — `license = { text = "AGPL-3.0-only" }` → `license = { text = "MIT" }`.
   Confirmed via `git diff` that this is the only changed line in the file (line 8's `description`
   and line 17's `mcp[cli]` dependency are untouched — those belong to P1.S2).
3. `README.md:380` — `Vocky is licensed under the GNU Affero General Public License v3.0. See
   [LICENSE](./LICENSE).` → `Vocky is licensed under the MIT License. See [LICENSE](./LICENSE).`
   Confirmed via `git diff` that this is the only changed line; the `## License` heading on line
   378 is untouched.

## Validation

- `grep -riE "AGPL|Affero|GNU|Public License" LICENSE pyproject.toml README.md` → **zero matches**
  (exit code 1 / no hits). No "AGPL", "Affero", "GNU", or "Public License" strings remain anywhere
  in the three files — even cleaner than the plan's minimum bar (the plan allowed the bare word
  "License" in the README `## License` heading, but that heading doesn't match the
  `Public License` sub-pattern anyway, so there was nothing to exempt).
- `grep -n "MIT" LICENSE pyproject.toml README.md` → PASS, shows the new MIT declarations in all
  three files:
  - `LICENSE:1:MIT License`
  - `LICENSE:16:...WARRANTIES OF MERCHANTABILITY,` (incidental substring match on "MIT" inside
    "LIMITED" — expected noise, not a real hit)
  - `pyproject.toml:11:license = { text = "MIT" }`
  - `README.md:380:Vocky is licensed under the MIT License. See [LICENSE](./LICENSE).`
- Optional sanity: `uv run python -c "import vocky.app"` → PASS, `IMPORT OK` (license edit is
  runtime-inert, as expected).
- `python3 scripts/workflow.py validate` → PASS, `Workflow validation passed.`

## Doc impact

None. Per `phase.md`, the license is absent from every durable doc (`docs/current/*.md`), so this
slice has no doc-impact entry to add to the running list.

## Deviations from plan

None. All three edits applied verbatim as specified; verification commands match plan exactly and
passed.
