# Result — P14.S4: Public agent-feedback documentation (SKILL.md, README, docs/cli.md, doc impact)

**Verdict: done.** The agent-feedback contract is published in all three public documents, the
byte-parity gate passes, and `phase.md`'s Doc impact list has been swept to completeness for
`P14.REVIEW`. No `src/` file was touched; one web *test* line had to follow the SKILL.md renumbering
(see Deviations).

---

## 1. `skills/vocky-feedback/SKILL.md` (canonical) — the main deliverable

Extended, not rewritten: same voice, same copy-runnable commands, same branch-by-branch error table.

**New step 3, "What goes in which field (read this before you build a payload)"**, placed *before*
the three transport paths, because the mapping decides the payload for all of them. It carries:

- D3's mapping table — the user's feedback/sentiment **verbatim** (`답답함`, `감사`, `긍정`, `부정`,
  `짜증`, or a whole sentence) → `message` (required, non-blank, "do not paraphrase into your own
  voice"); the agent's note about what happened and why it was recorded → `comment` (*"optional in the
  schema, but treat it as required whenever an agent is the one recording"*); `recorded_by` the marker;
  `tags` optional; `source.integration` a free-text runtime hint and explicitly **not** the marker.
- `recorded_by` vs `trigger_type` — *who recorded this* vs *why capture happened*; set once at
  capture, not editable afterwards.
- **Omitting it does not mean `human`** — it stores `null` = *unspecified*, which is also what every
  pre-marker record reads back as. Then the three transport rules: `/mcp` ⇒ `agent`, REST and CLI ⇒
  `null`, explicit always wins.
- The rejection string verbatim, and a `json` example body (sentiment + note + explicit marker).

**Renumbering.** Paths A/B/C became 4/5/6, the error table 7, "Report back" 8; both in-text
`see the table in step 6` references were repointed to step 7.

**Other edits, all additive:**

| Where | What |
|---|---|
| Step 1 (setup) | New bullet: a `vk_` key is **not capture-only** — capture + read + PATCH + DELETE within its scope, org key = every project in the org; mint a **project-bound** key for an agent runtime, store it as a read-write secret. (D4 item 3) |
| Step 4 (CLI) | New bullet: there is **no** `recorded_by` flag; a `vocky capture` lands `null` (though `--comment` still carries the note); use Path B/C when the marker matters. |
| Step 5 (REST) | `recorded_by` added to the legitimate top-level field list; one bullet — REST does **not** infer the marker. |
| Step 6 (`/mcp`) | Retitled "the agent-runtime transport". States the tool takes `recorded_by`, that this is the one place the marker is inferred (`agent` on omission, so an agent that never learns the argument is still marked correctly), and that a rejected value returns an `isError` **tool result** carrying the same string — not an HTTP status (verified in `src/vocky/tools/capture_feedback.py:109-112`). |
| Step 6 gotcha | **Corrected a pre-existing factual error.** It claimed an unlisted host makes every `/mcp` call "401 regardless of the key". Per S3's live evidence it is **`421 Invalid Host header`**; the check is on the **`Host`** header (not `Origin`), the default allowlist is `127.0.0.1`/`localhost`/`[::1]` (`mcp_server.py:17`), the key is never examined, and `VOCKY_MCP_ALLOWED_ORIGINS` normally needs nothing because non-browser MCP clients send no `Origin`. |
| Step 7 (errors) | Two new rows: `400 recorded_by must be one of: agent, human` (closed vocabulary, omit rather than guess, MCP returns it as a tool error) and `421 Invalid Host header` (`/mcp` only, plain text, not a key problem, not retryable). |

**Not changed on purpose:** the YAML frontmatter. `description` governs when the skill activates in
every installed client; P14 changes *what to send*, not *when to capture*, and rewriting the trigger
sentence would be a behavior change to every adopter's skill. Recorded here so REVIEW sees it was a
decision, not an oversight.

**Byte parity:** edited the canonical only, then `cp skills/vocky-feedback/SKILL.md
web/public/SKILL.md`. The served copy was never hand-edited; `web/.prettierignore` untouched. The
landing pane computes its own line/byte counts at request time, so no frontend or count edit exists.

## 2. `README.md`

Every spot S2 pinpointed, verified against the current file first:

- **Quickstart capture curl** (~L103) — `"recorded_by": "human"` added.
- **Trigger-fields paragraph** (~L264) — a new paragraph after it: `recorded_by` answers *who
  recorded the event*, orthogonal to the trigger fields' *why*; `agent` | `human` only, else the 400
  string; omitting stores `null` = unspecified (never assume human; pre-marker records read `null`);
  `/mcp` is the one surface that infers `agent`; provenance, so not backfilled, not inferred, not
  Admin-PATCH-able.
- **Full REST example** (~L367) and the **Python `httpx` example** (~L399) — `"recorded_by": "human"`.
- **"Agent Capture Over MCP (write-only)"** (~L414) — `recorded_by` named as an MCP tool input, then
  two new blocks: **the agent-capture convention** (the `message`/`comment`/`recorded_by`/
  `source.integration` mapping, `comment` documented-required, the `/mcp` default) and **key scope,
  stated plainly** (not capture-only; mint project-bound for third-party runtimes; per-credential
  capture-only scopes not implemented yet), plus the `Host`-allowlist/`421` paragraph.
- **"Read Back Feedback"** — one paragraph: every read surface returns `recorded_by` in the record
  (`"agent"` / `"human"` / `null`) and accepts `?recorded_by=`; exact match; omitting returns
  everything; **no filter value selects only the `null` rows** (S2's finding).
- **Admin filters sentence** (~L446) — gained `recorded_by`, plus "deliberately **not** patchable".

## 3. `docs/cli.md`

**Confirmed hand-maintained, not generated** — nothing in `Makefile`, `scripts/`, or `.github/`
references it, and it is not under `docs/current/`. So direct editing is correct.

- §2a (`Store the vk_… key as a secret`, ~L221) — the key-scope reality + "mint a project-bound key
  for anything outside your own control".
- §4 capture example (~L266) — `"recorded_by": "human"` in the raw-HTTP body, and a new **"Marking who
  recorded it"** paragraph: the vocabulary + 400 string, `null` = unspecified not human, **`vocky
  capture` has no marker flag** so CLI captures are always unspecified (use REST or `/mcp`), and the
  who-vs-why distinction from `trigger_type`.
- §5 read-back — every read surface returns `recorded_by` and accepts the filter, with a copyable
  `/app/feedback?recorded_by=agent` example.
- MCP section (~L306) — `recorded_by` listed among the tool inputs, a bullet for the `agent` default +
  the tool-error rejection shape, the `message`/`comment` mapping paragraph (noting both are covered by
  `/app/feedback?q=` / `vocky feedback search`), and the project-bound-key line.

## 4. S3's must-nots — honored

- **`q` is never shown on a surface that does not have it.** Every mention is scoped to
  `/app/feedback?q=` or `vocky feedback search`; nothing implies `q` on admin, project, or
  `GET /api/feedback`.
- **No CLI marker flag is implied anywhere.** Both SKILL.md Path A and `docs/cli.md` §4 state
  affirmatively that `vocky capture` has no such flag and lands `null`, and route the reader to REST or
  `/mcp`. Filed as decision text rather than as a widening of the CLI (see the `decisions.md` Doc
  impact line, D-P14-3).

## 5. Doc impact completeness sweep

`docs/current/*.md` was **not** touched. The `phase.md` list was reconciled against every P14 change
(`git diff d8efbf3..HEAD` outside `works/`, plus this slice) and gained **six** lines:

| Doc | Why it was missing |
|---|---|
| `experience.md` | **The largest gap.** It is the product integration guide — capture field list (~L112–117), capture examples, "Agent Capture Over MCP" (~L198–232), end-user read filters (~L243) — and no slice had filed it. It is the durable-doc home of everything this slice published. |
| `product.md` | Its "the skill is a published artifact" bullet describes the skill's contents; the skill now also carries the agent-capture convention, the marker, and the key-scope statement, and is 8 steps not 7. |
| `security.md` | D4 item 3 asked for the `vk_`-key reality to be said out loud publicly; it now is, in three documents. S3's `security.md` line covered only the `/mcp` host allowlist. |
| `backend.md` | S1 added a whole new module (`src/vocky/recorded_by.py`) and the `normalize_mcp_payload` default seam; `backend.md` inventories exactly this kind of module surface and had no line. |
| `decisions.md` | D-P14-3: `comment` documented-required rather than server-enforced, and the CLI deliberately carrying no marker flag — both are standing decisions, not incidental. |
| `qa.md` | The SSR skill test pins SKILL.md's last section heading; any future section change touches it. |

## 6. Validation

| Command | Result |
|---|---|
| `make check-skill-parity` | **PASS** — `web/public/SKILL.md` byte-identical to the canonical (run twice: after the first copy and after the final Path A bullet) |
| `make test` | **238 passed** — identical to the S2/S3 baseline, as expected for a docs slice |
| `npm test` (web) | **78 passed / 10 files** — after the one-line test fix below; it failed 1/78 before it |
| `npm run typecheck` / `lint` / `format:check` (web) | clean |
| `python3 scripts/workflow.py validate` | `Workflow validation passed.` |
| `json.loads` on every JSON body edited (SKILL step 3, README quickstart + full example, `docs/cli.md` capture) | all 4 parse; `recorded_by` present in each |
| `ast.parse` on the README `httpx` Python example | parses |
| `prettier --check README.md docs/cli.md` | warns — **pre-existing**, verified identical at `HEAD`; repo-root markdown is outside `web/`'s `prettier --check .` scope, so CI does not check it. Deliberately not reformatted. |

## 7. Deviations from `plan.md`

1. **One file outside the plan's three was edited: `web/tests/skill-preview-ssr.test.ts` (one line).**
   Its "the whole file shipped, nothing truncated" probe asserts on the **last section heading**, which
   the renumbering moved from `## 7. Report back` to `## 8. Report back`. It is the SKILL.md analogue of
   S2's single exact-dict assertion — a mirror of the file, not a client contract — and its neighbouring
   line/byte assertions are computed from the file and needed nothing. Without the fix the web suite is
   red. No other assertion in `tests/` or `web/tests/` references SKILL.md content.
2. **The SKILL.md renumber itself** (7 sections → 8) is more churn than "extend, don't rewrite" might
   suggest. It buys the field mapping being read *before* the payload is built, which is the whole point
   of the contract for a third-party adopter; no prose in the shifted sections was rewritten.
3. **A pre-existing SKILL.md error was corrected** (`401` → `421` on the Host allowlist) beyond simply
   "keeping the paragraph accurate" — the plan flagged it as something to verify, and S3's evidence
   showed the claim was wrong.
4. **Extra spots edited beyond S2's pinpointed list** — README's "Read Back Feedback" and "Agent Capture
   Over MCP" sections, and three additional `docs/cli.md` spots (§2a, §5, the MCP section) — because the
   plan's "written so a third-party agent product can adopt it from the docs alone" bar is not met by the
   payload examples alone.
5. **The SKILL.md frontmatter `description` was deliberately left alone** (see §1) — changing skill
   activation semantics for every installed client is not this slice's job.

## 8. Files changed

- `skills/vocky-feedback/SKILL.md` (canonical)
- `web/public/SKILL.md` (byte-identical `cp`, never hand-edited)
- `README.md`
- `docs/cli.md`
- `web/tests/skill-preview-ssr.test.ts` (one line — see Deviations)
- `works/phases/active/P14/phase.md` (S4 cross-slice notes + 6 new Doc impact lines)
- `works/phases/active/P14/slices/P14.S4/result.md` (this file)
