# Result — P15.REVIEW: Phase review of P15 (New-maintainer knowledge base)

**Verdict: `pass`.** Every slice's output exists and matches what its `result.md` claims, the phase
delivers exactly what `intent.md` confirmed, and the doc-impact picture is genuinely empty — so this
review consolidates **no** doc versions. Three advisory findings are recorded below; none of them is a
defect in P15's own work, and none of them requires a fix slice.

## 1. Validation

### State integrity

| command | outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **pass** — "Workflow validation passed." (exit 0) |

### S5 (README audit) — re-run behaviorally

| check | expected | actual |
|---|---|---|
| `grep -n "package-check" README.md` | no match | **no match** (exit 1) |
| `grep -niE "not live\|once.*is live\|before the site is deployed" README.md` | no match | **no match** (exit 1) |
| `grep -n "VOCKY_SMTP" README.md` | present | **2 matches** (lines 171, 194) |
| `grep -n "check-skill-parity" README.md` | present | **1 match** (line 240) |

Beyond the greps:

- **Every `make` target the README claims exists.** Cross-read `Makefile` `.PHONY` (line 18):
  `sync test compose-up compose-down compose-logs migrate wait-ready smoke-run smoke bootstrap verify
  check-test-db require-external-base-url external-smoke external-verify check-skill-parity`. The
  README's granular list and prose targets are all in it; `package-check` is genuinely absent, so the
  removed bullet was correct. The rewritten `make verify` sentence ("waits for `/healthz`, runs the REST
  smoke flow, then the full pytest suite — `smoke test`, no packaging step") matches `Makefile:57`
  (`verify: smoke test`) exactly.
- **Edited sections read coherently.** Re-read §Surfaces (line 28), §Install (lines 48–75), §What The
  Current Pre-MVP Does (lines 160–172), §Current Status (lines 186–196) in place. The install section's
  framing flip is clean: hosted `curl | bash` is now stated as live and primary, and the checkout options
  are re-framed as the develop-against-this-checkout / no-curl-pipe alternative with no orphaned "once…"
  hedge left behind. Anchors resolve: `#install` → `### Install` (line 48);
  `#agent-capture-over-mcp-write-only` → `## Agent Capture Over MCP (write-only)` (line 421).
- **Audit, not rewrite** (the intent's explicit constraint): `git show --stat 03c1605 -- README.md` →
  **1 file, 11 insertions, 7 deletions**. Section order, headings, and code examples are untouched.
- **Facts trace to accurate durable docs.** The added "nothing is published to PyPI" and the hosted-line
  claim match `docs/current/operations.md:26` verbatim in substance; the five `VOCKY_SMTP_*` vars match
  operations.md's P13 section.

### S1–S4 (the explainer series) — outputs exist in the KB

KB reachable at `https://knowledge.hi2vi.com` with `api.token` from `~/.config/knowledge-kb/config.json`.
`GET /api/documents?project=vocky&limit=50` → **HTTP 200, `total: 4`**:

| id | version | title | rel_path | recorded by |
|---|---|---|---|---|
| 25 | v1 | Vocky: What It Is and How It Is Used | `vocky/2026-08-06-vocky-what-it-is-and-how-it-is-used.html` | S1 `result.md` ✅ exact match |
| 26 | v1 | Vocky System Internals: Architecture, Code Map, Data Model, and Contracts | `vocky/2026-08-06-vocky-system-internals-…-and-contracts.html` | S2 `result.md` ✅ exact match |
| 27 | v1 | Vocky Security, Operations, and QA: Keeping It Safe and Keeping It Running | `vocky/2026-08-06-vocky-security-operations-and-qa-…-running.html` | S3 `result.md` ✅ (id + v1 match; rel_path not recorded there) |
| 28 | v1 | Vocky Decisions, History, and the Agentic Workspace: Why It Is This Way and How to Change It | `vocky/2026-08-06-vocky-decisions-history-…-how-to.html` | S4 `result.md` ✅ exact match |

Four documents, ids 25–28, all `version: 1`, all `project: vocky`, created 22:53 → 23:07 on 2026-08-06 in
slice order. No extra or orphaned documents in the project.

**Body spot-sanity** (`GET /api/documents/by-path/…`, extracted text length, not a prose review):
doc 25 → 18,037 chars; doc 26 → 20,302; doc 27 → 18,292; doc 28 → 14,716. Each carries the `/explain`
section skeleton (Background / Intuition / Code / Quiz), and doc 26 opens with the explicit series framing
("Second of a four-part series for a new vocky maintainer…"), confirming the four were written as an
ordered series rather than four unrelated pages. None is empty or truncated.

**Gotcha worth recording:** the KB API rejects Python `urllib` with **403 Forbidden** (user-agent
filtering at the edge) while the identical `curl` request with the same bearer token returns 200. Use
`curl` for KB verification, as `/explain`'s own skill does.

## 2. Judgment against the objective and `intent.md`

| what was asked | delivered | verdict |
|---|---|---|
| A **series** of `/explain` explainers giving a **new maintainer** full understanding, saved to the personal KB; operator capped the series at 3–5 substantial ones | Four explainers, KB 25 → 26 → 27 → 28, in a deliberate reading order (what it is → how it works → how it is kept safe/running → why it is this way) | ✅ |
| Full coverage of the corpus | The decomposition's mapping lands each of the **eleven** `docs/current/*.md` in exactly one explainer (`ls docs/current/` confirms exactly those eleven), plus `docs/cli.md`, the skill, `src/vocky/`, `web/`, the deploy kit, `CLAUDE.md`/`works/`. Every slice's `result.md` records what it actually grounded in, and S2/S3 both explicitly answered the phase's open question ("one run sufficed, no re-split") instead of silently thinning coverage | ✅ |
| **Personal-KB-only** delivery — no `here` copies, nothing under `docs/` or `works/` gaining explainer content | No `*.html` anywhere in the repo root; `find -iname "*EXPLAINED*"` → nothing; `git ls-files \| grep -iE "explain\|EXPLAINED"` → nothing tracked. The four knowledge commits touch only `works/` bookkeeping (`plan.md`, `result.md`, `phase.md`, `slice.json`, dashboards). Each `result.md` states "no `here` flag" | ✅ |
| README **audit, not rewrite** | 11 insertions / 7 deletions across one file, all six recorded staleness items fixed, structure intact | ✅ |
| Scope stays new-maintainer only (user/contributor knowledge deferred out, per `intent.md` §Notes) | No slice strayed into user- or contributor-facing material | ✅ |

The phase's product is understanding, and the evidence that it landed is concrete: four published,
substantial, ordered documents plus a README that no longer contradicts them.

## 3. Doc impact and consolidation

**`doc_versions: none.` Nothing to consolidate — and that is the correct outcome, not an omission.**

The recorded picture is empty and I agree with each link in it:

- **DECOMP** — none (planning only).
- **S1–S4** — none by construction: the explainers live in the operator's personal KB, not in this repo,
  so they change no durable truth here. This is a phase constraint, not an oversight.
- **S5** — explicitly decided "no new Doc impact note", with a reason I verified independently: every fact
  S5 added to the README is *already correctly stated* in `docs/current/operations.md` (live since
  2026-08-04; the hosted installer works; still not on PyPI, by decision; the five `VOCKY_SMTP_*` vars;
  `check-skill-parity` as a CI gate). S5 pulled the README **up to** accurate durable docs; it did not
  discover new durable truth. `README.md` is not under `docs/`, so it is not itself versioned.

A `doc-new-version` run here would produce a version whose changelog entry is "nothing changed", so this
review creates none.

## 4. Findings

None of these blocks the pass.

### Finding 1 (advisory, real, pre-existing) — stale pre-P12 "not live" text still inside `docs/current/`

S1's finding is **confirmed against the files**, and the contradiction is sharper than recorded:

- `docs/current/product.md` (v0012) **line 22**: "nobody outside this repo can use vocky … `vocky.hi2vi.com`
  does not answer … Public availability now needs exactly one more phase: **P12**" — while **line 96** of
  the same file says "**vocky is live at `https://vocky.hi2vi.com`** (since 2026-08-04, P12)".
- `docs/current/product.md` **line 94** (§Distribution): "Two facts … both currently **not yet true in the
  world**" — one of the two (the hosted installer) is true today.
- `docs/current/experience.md` (v0013) **line 14** (opening blockquote): "There is no hosted vocky yet:
  `https://vocky.hi2vi.com` is not live … today, before the site is deployed, the CLI still installs from a
  checkout".
- `docs/current/experience.md` **line 346** (§The Web App): "(It runs locally today; `vocky.hi2vi.com` is
  **not live** — the deploy kit is authored but unexecuted, and bring-up is P12.)" — while **line 414** of
  the same file already declares "**Any 'once the site is live' hedging in older copy is now historical**".

So `experience.md` explicitly labels its own line-14/line-346 wording as historical, 60 lines later. Both
files are internally self-contradicting, and a new maintainer reading top-down hits the false statement
first. Root cause is the same P12 doc pass that also left the README stale — the P12/P14 doc versions added
the new truth without sweeping the old hedges.

**This is out of P15's scope** (P15 never touched those docs; its objective was explainers + a README
audit), so it is **not** grounds for `changes_requested` — reopening the phase would misattribute
pre-existing debt to it. **Recommended shape — recommendation only, not executed here:**

1. **Preferred: a standalone doc-only fix** (`CLAUDE.md` §Standalone Work explicitly permits durable-truth
   standalone changes provided they go through `doc-new-version`). Two versions:
   - `doc-new-version --doc product --summary "Retire the pre-P12 not-live hedges left in the status and distribution sections"`
   - `doc-new-version --doc experience --summary "Retire the pre-P12 not-live hedges in the opening note and the web app section"`
   The edit is **deletion/redirection of four passages**, not new research: the corrected facts already sit
   in the same two files (`product.md:96`, `experience.md:404–414`) and in `operations.md:26`. Then
   `rebuild-docs`. Scope it tightly — do not re-audit either doc wholesale.
2. **Fallback if the operator would rather queue it:**
   `defer-job --title "Sweep pre-P12 'not live' hedges out of product.md and experience.md" --reason "Both docs contradict their own live-since-2026-08-04 text; a new maintainer hits the false statement first" --trigger "Before the next product/experience doc version, or on the next docs-facing phase" --source P15.REVIEW`.
3. **Not recommended:** a `P15.F1` fix slice. It would require a `changes_requested` verdict to reopen a
   phase whose own work is complete and correct.

### Finding 2 (cosmetic bookkeeping) — the README line count is off by one in two places

`P15.S5/result.md` and `phase.md` both say "476 → **481** lines (net +5, 11 insertions / 7 deletions)".
The insertion/deletion counts are right (`git show --stat 03c1605`), but the arithmetic is not:
`git show 03c1605~1:README.md | wc -l` → **476**, `git show 03c1605:README.md | wc -l` → **480**
(net **+4**). No content or behavior implication whatsoever. I did not edit another slice's `result.md`;
the correction is appended to `phase.md` instead.

### Finding 3 (workspace-level observation, not a P15 defect) — `phase.json` never left `planned`

P15's `phase.json` still reads `"status": "planned"` with `"started_at": null` even though DECOMP and
S1–S5 are all `done`. This is **not** specific to P15: `start-slice` does not transition the phase
(`scripts/workflow.py:893` just delegates to `set_slice_status`), and P8, P9, P10, P11, P12, P13 and P14
all show the same `started_at: null` in their archived `phase.json` (only P6 has one). `validate` accepts
it, and `review-phase pass` will set `status: done` + `completed_at` as usual. The only cost is that the
archived record never carries a start timestamp. Flagged for the operator's awareness — either an engine
change (have `start-slice` promote a `planned` phase to `in_progress`) or an accepted convention; **not**
something for this phase to fix.

## 5. Workflow integrity

| check | result |
|---|---|
| Slice statuses | `DECOMP` + `S1`–`S5` all `done`; `REVIEW` `in_progress` (correct mid-review). Orders 0,1,2,3,4,5,9999 — no gaps, no collisions |
| `plan.md` present per slice | ✅ all seven |
| `result.md` present per executed slice | ✅ DECOMP + S1–S5 (REVIEW's is this file) |
| Commits at slice boundaries | ✅ exactly six, one per slice, in order: `4dfbc59` DECOMP → `87d6742` S1 → `00fe998` S2 → `233c9e2` S3 → `6fb2824` S4 → `03c1605` S5. Conventional-commit form throughout |
| Repo-file blast radius | ✅ only `README.md` (S5) plus `works/` bookkeeping and a regenerated `docs/index.json` `last_rebuilt_at` timestamp in the DECOMP commit — exactly the phase's stated constraint |
| Inline-execution rule for `knowledge` slices | ✅ S1, S2, S3 and S4 `result.md` each state the `/explain` run was "executed inline by the orchestrator"; no `slice-executor` was dispatched for any of them, matching the rule recorded in `phase.md` §"Execution rule". S5 (the only dispatchable slice) was dispatched normally |
| Uncommitted at review time | the expected `start-slice` bookkeeping (`works/state.json`, dashboards, `events.jsonl`, `P15.REVIEW/slice.json`) plus this slice's `plan.md`/`result.md`. Nothing stray |

One note on the `--risk low` on S1–S4: per `phase.md` that is nominal bookkeeping for inline slices and
explicitly does **not** mean "dispatch to `slice-executor-mid`". The recorded rule was honored, so the
tier-selection contract was not violated — but the `risk` field is doing double duty for `kind: knowledge`
slices, which is worth remembering if a future phase adds more of them.

## 6. Verdict

- `review_verdict`: **pass**
- `doc_versions`: **none** — the phase's doc-impact picture is legitimately empty (see §3)
- `explain`: not written — run `/explain` for this phase

## Deviations from `plan.md`

None. All six review tasks were carried out as written; per the plan, Finding 1 is a **recommendation**,
not an executed doc edit, and no `doc-new-version` was run.
