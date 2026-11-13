# P8.REVIEW — phase review: validate the gate, consolidate the docs

`review` / `risk: medium`. Read + doc-write only — **never touch `web/` source.** Return a `review_verdict`.

Read `phase.md` (its *Findings & Notes*, *Constraints*, *Doc impact*) and `intent.md` first. The three
done slices are `P8.DECOMP`, `P8.S1`, `P8.S2`.

## Context

P8 ran the Claude Design gate that P4 deferred (D-P4-3). `P8.S2` closed it: handoff → operator session →
read-back → the signed-off design landed at `docs/reference/design/`. This review validates the phase
against its objective and `intent.md`, and — **only on a passing review** — consolidates the phase's
"Doc impact" notes into new doc versions. This is the one slice permitted to run `doc-new-version`.

## Validate

1. **State integrity:** `python3 scripts/workflow.py validate` clean.
2. **Each slice, re-run together:**
   - `P8.DECOMP` — two middle slices created, bare folders, correctly typed (`P8.S1` impl/low, `P8.S2`
     co-work/high depends-on P8.S1). No behavioral test.
   - `P8.S1` — from `web/`: `pnpm typecheck` and `pnpm lint` **pass**; `test ! -e web/design`;
     `grep -rn "design/canvas" web/` empty. **`pnpm format:check` fails on 20 pre-existing P4 files
     unrelated to this phase** — known debt, documented in `P8.S1`/`phase.md`, **NOT a review blocker.**
     Confirm neither `page.tsx` nor `.prettierignore` is in the warning list.
   - `P8.S2` — no code. Verify the record is coherent: `docs/reference/design/rounds/01-brand-app-landing/`
     holds `handoff.md`, `handoff-02-cards.md`, `output/{result.md,build-prompt.md}`; `SIGNOFF.md` exists;
     `build-prompt.md` is a complete buildable contract (exact token values, component APIs, per-file
     manifest, DoD). The 30-card set is correctly left in the design project, **not** copied down.
3. **Against objective / `intent.md`:**
   - The phase did what it set out to: handoff → session → read-back → landed spec. Implementation is P9.
   - **Zero brand decisions by Claude Code** (the load-bearing constraint): every palette/type/copy call is
     the operator's, recorded in `result.md` §0/§6. Verify no slice proposed a palette or answered a design
     question.
   - **Constraints honored:** canvas retired (8); `/design-sync` never run (9); no `web/package.json`
     `"types"` patch; docs versioned only here (10); the design slice wrote no impl code and was never
     dispatched; P6 untouched (7).

## Doc consolidation — ONLY on a passing review, narrow and careful

`docs/current/` says "P6" for **two different things**. Consolidate only the **design gate**; leave the rest.

- **CONSOLIDATE (design gate — now P8/P9, closed):**
  - **`frontend.md`** — (a) **drop the `web/design/canvas/` section** (the tree was deleted by P8.S1): the
    file-tree line (~57) and the detailed `design/canvas/` bullet (~74). (b) Correct the design-gate
    forward-refs from "deferred to P6" → "closed at P8, applied by P9", pointing at `docs/reference/design/`:
    the "Design System (ported, P6-swappable) — D-P4-3" section (~63–68); `TrendChart` "a real chart library
    is a P6 design-gate question" (~152 → resolved: redesigned, kept dependency-free); the "P6-swappable"
    notes (~183); "keep the placeholder palette's token names stable so the P6 gate swaps values only"
    (~205 → gate closed; light-only confirmed; names-kept value swap to deep-emerald specified for P9).
    **Keep frontend.md describing the current *placeholder* state as still-live** — P9 applies the new
    design; do not write the new palette up as if it shipped.
  - **`decisions.md`** — add a **new decision** (`D-P8-1`) recording round 01's resolution (vocky
    deep-emerald brand via names-kept value swap, Pretendard, light-only, the new component vocabulary, the
    landing reclaiming `/`, loading/error/404 states, **no backend change**) and that it **supersedes
    D-P4-3**, moving the landing design+build into P8+P9. Old versions are immutable — the new version marks
    D-P4-3 superseded, it does not rewrite it.
- **DO NOT TOUCH (legitimately still P6):** every "P6" reference about the **packaged Admin Web UI physical
  removal** (`architecture.md`, `product.md` ~36/61, `experience.md` ~310, `api.md`) and the **production
  deploy** (`operations.md` ~59/73). Constraint 7: do not touch P6 — reconciled at `P6.DECOMP`.
- **`experience.md`** — confirm its "P6" mentions are Admin-UI removal, not the design gate; it documents
  the *shipped* (placeholder) experience, so do **not** rewrite it to the new design. Most likely **no new
  version**.

`doc-new-version --doc frontend --summary "..." --source P8.REVIEW` and
`doc-new-version --doc decisions --summary "..." --source P8.REVIEW`, then `rebuild-docs`. Never hand-edit
`docs/current/*.md` (generated); versions live under `docs/versions/`.

## Boundaries

- **Do not commit; do not transition phase/slice status.** The orchestrator records the verdict via
  `review-phase` and commits. Return `review_verdict` (`pass|changes_requested|blocked`) with findings.
- `doc-new-version` is allowed **only** here, **only** on a `pass`. On `changes_requested`/`blocked`, do not
  version docs — list what must change.
- Write `result.md` (free-form). Append durable notes to `phase.md`.
- No `web/` source edits. No editing the read-only `output/` record. No archiving. No P9 work.
