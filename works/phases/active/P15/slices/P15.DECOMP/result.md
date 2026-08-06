# Result — P15.DECOMP

## What I did

Surveyed the workspace for topic scoping (all eleven `docs/current/*.md` headings plus full reads of
`product.md` and the bulk of `architecture.md`; `README.md` structure and three spot-reads; the `src/vocky/`
tree, `pyproject.toml`, `web/src/`, `deploy/`, `tests/`, `.github/workflows/`, `Makefile`, `skills/`), then
cut the phase into **five middle slices**: four `kind: knowledge` explainer slices meant to be read in order
as a short series, and one docs-only README audit last.

## Slices created (bare folders — no `plan.md` pre-filled)

| id | name | kind | risk | order |
|---|---|---|---|---|
| `P15.S1` | Knowledge: the product and its user-facing surfaces | `knowledge` | `low` | 1 |
| `P15.S2` | Knowledge: system internals — architecture, backend code map, data model, API contracts | `knowledge` | `low` | 2 |
| `P15.S3` | Knowledge: security, operations, and QA | `knowledge` | `low` | 3 |
| `P15.S4` | Knowledge: decisions, history, and the agentic workspace | `knowledge` | `low` | 4 |
| `P15.S5` | Audit and refresh README.md | `implementation` | `low` | 5 |

Every folder contains only `slice.json` (verified on `P15.S1` and `P15.S5`); orders are contiguous 1–5 with
`P15.REVIEW` at 9999, and the README audit is last.

## Topic rationale (brief)

Four substantial explainers, each answering the next question a new maintainer asks: *what is it and how is
it used* (S1) → *how does it work* (S2) → *how is it secured and operated* (S3) → *why is it like this and
how do I change it* (S4). Each `docs/current` doc lands in exactly one explainer, so overlap stays minimal:
S1 ← `product` + `experience` + `frontend` + `docs/cli.md`; S2 ← `architecture` + `backend` + `data` + `api`;
S3 ← `security` + `operations` + `qa`; S4 ← `decisions` + the workspace contract.

Two grouping calls, recorded in `phase.md`: **clients live with the product (S1), not the internals** — the
web app and CLI add no backend capability, so they belong to the "how vocky is used" story; and **security
sits with operations (S3), not architecture** — credential scope, the fail-closed admin guard, the
single-worker rate-limiter invariant and `/mcp` host allowlisting are all things an operator must configure
and verify, so they read naturally alongside the deploy topology and the CI gates.

## Consolidation (operator feedback, mid-slice)

My first pass cut **ten** narrow knowledge slices (`P15.S1`–`P15.S10`) plus a README slice. The operator
judged that too fine-grained and asked for 3–5 knowledge slices total. I deleted all eleven bare folders
(`rm -rf works/phases/active/P15/slices/P15.S1 … P15.S11` — unstarted, `plan.md`-free folders created in this
same slice) and re-created the consolidated set above with `new-slice`, renaming rather than reusing so each
`slice.json` name reflects its merged scope. `phase.md` §Decomposition and §Findings & Notes were rewritten
to the consolidated cut: merged per-topic source lists, the preserved inline-execution rule, and the six
README staleness findings all carried over. A one-line note records the superseded ten-slice pass and names
the natural re-split (S2) should a later run ever need one.

## Validation

- `python3 scripts/workflow.py validate` → **passed** (run against the first, ten-slice cut; **not** re-run
  after consolidation, per the orchestrator's instruction to leave state regeneration to it).
- Slice-table dump after consolidation → orders 1–5 contiguous, all `todo`, kinds/risks as intended,
  `P15.REVIEW` still at 9999.
- `ls` on `P15.S1` / `P15.S5` → each holds only `slice.json` (no pre-filled `plan.md`).
- **The orchestrator should run `rebuild` + `validate` before committing** — the deleted folders mean the
  generated dashboards (`works/backlog.md`, `works/index.json`) still list the retired `S6`–`S11` ids.

## What the orchestrator should know

1. **`knowledge` slices are inline-only.** `/explain` is a user-level Claude Code skill
   (`~/.claude/skills/explain/`) and does not exist inside a `slice-executor`. All four `kind: knowledge`
   slices must be run by the orchestrator on the main thread; `--risk low` on them is nominal bookkeeping and
   must **not** be read as "dispatch to `slice-executor-mid`". Only `P15.S5` is dispatched normally.
2. **The knowledge base is configured** — `~/.config/knowledge-kb/config.json` resolves `kb_root` to
   `/Users/sugang/projects/personal/knowledge` (has `mkdocs.yml`), so `/explain` will not stall on setup.
   Invoke in topic mode and **without** the `here` flag (the confirmed intent is personal-KB only).
3. **Merged per-topic source lists** for all four explainers are in `phase.md` §Findings & Notes, so each
   knowledge slice's plan can name its reading set without re-surveying. Because the topics are broad, each
   plan should state the whole grouping in the `/explain` topic string.
4. **Six concrete README staleness findings** are already recorded for `P15.S5` (live deployment vs "public
   deployment is P6", the inverted installer framing, the removed `make package-check` / mis-described
   `make verify`, missing P13 SMTP alerts, and two stale status sections).
5. Open questions left in `phase.md`: whether a README-only correction warrants a "Doc impact" note (only if
   it also contradicts `docs/current/*.md` — S5 decides explicitly), and a note that S2/S3 are the heavy
   explainers, to be flagged in their `result.md` if one `/explain` run cannot cover the grouping.

## Doc impact

None. Decomposition changed no durable truth.

## Deviations from `plan.md`

The plan said to choose "as many knowledge topics as full coverage genuinely requires — one slice per topic",
and my first pass read that as ten. Mid-slice operator feedback capped the series at 3–5 knowledge slices, so
the final cut is four; the ten surplus bare folders were deleted and replaced. Per the same instruction I did
**not** re-run `rebuild` or `validate` after consolidating — the orchestrator regenerates state.
