# Plan — P14.S4: Public agent-feedback documentation: SKILL.md, README, doc impact

## Job

Publish the agent-feedback contract that S1–S3 built and proved. Read `works/phases/active/P14/phase.md` in full first — D1–D4, the SKILL byte-parity findings, and the S1/S2/S3 cross-slice notes (S2 lists the exact README/`docs/cli.md` spots; S3 lists what must NOT be documented). This is the public contract: write it so a third-party agent product (changple being the first) can adopt it from the docs alone.

## Scope

1. **`skills/vocky-feedback/SKILL.md` (canonical) — the main deliverable.** Add the agent-capture convention as a first-class part of the skill:
   - The field mapping (D3): the user's feedback/sentiment, free text, verbatim where possible (답답함, 감사, 긍정, 부정, 짜증, or a whole sentence) → `message`; the agent's free-text note about it (what happened, why it was recorded) → `comment` — **documented as required for agent capture** (schema-optional; the server does not enforce it); optional `tags`; runtime in `source.integration` (still free text, still not the marker).
   - `recorded_by` (D1/D2): values `agent` | `human`, omitted = `null`; **`/mcp` defaults it to `"agent"` when omitted, REST does not** — an explicit value always wins. Bad value → 400 `recorded_by must be one of: agent, human` (add to the step-6 error table).
   - Path C (`/mcp`) is the natural agent-runtime transport — keep the existing self-hosting `VOCKY_MCP_ALLOWED_HOSTS` gotcha accurate per S3's findings (non-browser clients send no `Origin`; unlisted non-localhost Host → `421`... verify the current paragraph's "401" claim against S3's evidence and fix if wrong).
   - **Key-scope honesty (D4 item 3)**: state plainly that a `vk_` key is NOT capture-only (capture + read + PATCH + DELETE across its scope) — for an agent runtime, mint a **project-bound** key, never an org key.
   - Keep the skill's voice and structure (copy-runnable commands, branch-by-branch errors); extend, don't rewrite.
2. **Byte parity**: after editing the canonical, `cp skills/vocky-feedback/SKILL.md web/public/SKILL.md`; `make check-skill-parity` must pass. Never hand-edit the served copy; the landing pane needs no count edits.
3. **README + `docs/cli.md`** per S2's pinpointed spots (payload/response examples ~L113/L367/L399, the trigger-fields paragraph ~L264, the admin-list-filters sentence ~L446; `docs/cli.md` ~L266 — verify each against the current files): add `recorded_by` to the capture-payload and read-response examples and the filter list. **Check first whether `docs/cli.md` is generated or hand-maintained** (it is not under `docs/current/`, so hand-editing is expected to be fine — confirm).
4. **Must-nots from S3**: do not document `q` search on admin/project/`GET /api/feedback` surfaces (it exists on `/app/feedback` only); do not document a CLI `recorded_by`/marker flag — the CLI deliberately does not carry it (S1/S2 notes); if the docs would imply one, phrase around it (the CLI is a human-driven path; its captures are `null`/explicit-REST territory).
5. **Doc impact completeness sweep**: `docs/current/*.md` are REVIEW-consolidated — do NOT hand-edit them. Instead, reconcile `phase.md`'s "Doc impact" list against everything P14 actually changed (S1–S4 inclusive, including this slice's own SKILL/README changes if any durable-truth doc mentions them) and add any missing one-line notes so REVIEW can consolidate in one pass.

## Constraints

- Additivity in docs too: existing documented behavior stays accurate; you are extending the contract's documentation, not changing tone or structure.
- Never edit `docs/current/*.md` or run `doc-new-version`.
- `web/.prettierignore` excludes `public/` — leave that alone.

## Validation

`make check-skill-parity`; `make test` (nothing should change — baseline 238); if README/docs examples are executable, sanity-check the JSON in them parses (e.g. `python3 -c 'import json; ...'`). Re-read the final SKILL.md start-to-finish as a third-party adopter and fix anything that doesn't stand alone.

## Deliverables

- Edited canonical SKILL.md + byte-identical served copy, README, `docs/cli.md` (if hand-maintained).
- `result.md` in this slice folder.
- Cross-slice notes + any missing Doc impact lines appended to `phase.md`.
- Structured verdict.
