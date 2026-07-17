# P8.DECOMP — decompose the design gate

## Context

**P8 is vocky's real Claude Design gate** — the one P4 deferred (**D-P4-3**) — re-created on 2026-07-17
under workspace v12 after the first attempt was fully reverted at `c9102e3`. The phase's own notebook
already carries every measured fact this decomposition needs; `phase.md` says plainly **"Do not
re-derive them."** The orchestrator verified the state rather than re-measuring it:

- Canvas today = **10 cards** — 3 foundations, 6 components, and `sections/dashboard-placeholder.html`
  (fictional, to be deleted). No `data-table` card, no hi2vi reference card, **no card mirrors a real
  shipped surface**.
- `docs/reference/design/` does not exist — vocky uses the living `web/design/canvas/**` mirror, which
  the `design-cowork` skill explicitly permits as the alternative record.
- `main` is **38 commits ahead** of `origin/main` on the public `github.com/leetusik/vocky`.
- `make bootstrap` (compose-up + migrate + wait-ready), `make smoke`, and `web`'s
  `build`/`start` (`next start -H 127.0.0.1 -p 3030`) all exist — the frozen baseline render needs no
  new deps and no Playwright.
- `executors.toml` is all-defaults → **flex mode**: `low` = sonnet@xhigh, `mid`/`high` = opus@xhigh.
  So `medium` vs `high` costs nothing extra; **`low` is the only real cost lever, and nothing here is
  mechanical enough for it.**

**This slice creates P8's middle slices — bare folders — and records the breakdown and rationale in
`phase.md`. It writes no cards, no code, and no other slice's `plan.md`.**

## What binds this decomposition

Non-negotiable, from `phase.md` → *Decomposition* / *Constraints*, `intent.md`, and the
`design-cowork` skill:

1. **The gate slice is `--kind co-work --risk high` and is NEVER dispatched** — the deliberate
   exception to "every slice is delegated", because executors have no `DesignSync` tool. Push, STOP,
   and read-back all live in that one slice (two commits, with the `pending` window between them).
2. **Do not over-plan before the gate** — *"you do not know what the operator will design."* **Round 1
   only**: `intent.md` fixes the shape as **seed → brief → gate → synthesis**. If the session needs a
   round 2, cut it at a fractional order *afterward*.
3. **Zero brand decisions** — the load-bearing constraint. No slice proposes a palette, a type
   direction, or landing copy. **Never answer a design question — pose it back.**
4. **`/design-sync` is forbidden here** (the anti-finding). The `DesignSync` *tool* is the mechanism.
5. **Docs are versioned once, at `P8.REVIEW`.** No middle slice runs `doc-new-version`; durable-truth
   changes get a one-line *Doc impact* note in `phase.md`.
6. **Ground in real content and real data shapes — never lorem.** A card with nothing real to mirror is
   invention: **don't author it, ask for it.**

## The shape to create

`intent.md`'s four stages, with **seed** split three ways on measured size (~11 cards at 100–330 lines
each, plus a machine-produced render). `P8.REVIEW` is at order 9999, so 1–7 slot in cleanly.

| Slice | Name | Kind | Risk | Order | Depends on |
|---|---|---|---|---|---|
| `P8.S1` | Frozen baseline render of the 6 shipped surfaces | `implementation` | `medium` | 1 | — |
| `P8.S2` | DS cards: foundations completion, DataTable card, `Reference — hi2vi vibe`; drop the fictional placeholder | `implementation` | `high` | 2 | — |
| `P8.S3` | Surface mirror cards A: app shell, login/signup, dashboard | `implementation` | `high` | 3 | `P8.S1` |
| `P8.S4` | Surface mirror cards B: project detail, feedback list, feedback detail | `implementation` | `high` | 4 | `P8.S1` |
| `P8.S5` | Gate brief card + `_ds_manifest.json` regen + P6→P8 source fixes | `implementation` | `high` | 5 | `P8.S2`, `P8.S3`, `P8.S4` |
| `P8.S6` | **The design gate: push → STOP → read-back** | **`co-work`** | **`high`** | 6 | `P8.S5` |
| `P8.S7` | Synthesis: capture the spec into `phase.md` + write the SIGNOFF | `implementation` | `high` | 7 | `P8.S6` |

Names above are the intent, not a required verbatim string — keep them recognisable and terse.

### Why this split

- **`S1` first, and it is not optional.** v12 requires *"a frozen baseline render of today's look…
  that survives token changes — the before/after reference at sign-off."* `phase.md` proves why it must
  precede the gate: utilities compile to `var(--color-*)` references, **so the instant the gate swaps
  `--color-green`, every live artifact re-themes and "before" is destroyed.** Its output is also the
  real paint `S3`/`S4` mirror against — hence the `depends_on`.
- **`S2` is design-system vocabulary; `S3`/`S4` are product surfaces.** Different work, different
  reference material. `S2` needs no baseline.
- **`S3`/`S4` split 3/3 by measured weight.** Feedback detail alone is ~2–3× the dashboard (5 sections,
  a 14-cell `<dl>`, tag pills, comment cards, attachment rows, collapsible JSON), and project detail is
  a 6-column table plus the show-once key panel. One slice of six cards is ~1200 lines of hand-authored
  HTML; two of three is reviewable.
- **`S5` last before the gate** because the manifest **does not rebuild on upload** — it can only be
  regenerated once every card exists.
- **Risk = `high` on every card-authoring slice** deliberately. In flex mode that costs the same as
  `medium`, and the constraint these slices can most easily break — *zero brand decisions* — is exactly
  the kind a literal plan-follower crosses without noticing. `S1` is `medium`: a build/curl/inline chain
  with real environment surprise but no design judgment. **Nothing here is `low`.**

### What is deliberately NOT sliced

- **No landing mirror cards.** The landing does not exist in code (`web/src/app/page.tsx` is a pure
  redirect), so authoring hero/features/pricing/footer cards would be **invention, not mirroring** —
  the exact trap constraint 6 and the fictional `dashboard-placeholder.html` both name. The landing
  reaches the session **through the brief, as questions** (*"a card can be a question"*). Claude Design
  designs it; we ask for it.
- **No loading / error / 404 cards.** `phase.md`: *"Cards for these would be net-new design, not
  mirroring."* They are already an Open Question for the brief.
- **No round 2, no apply slices.** Round 1 only; P9 owns the apply.

## What this slice must record in `phase.md`

Fill the empty **Decomposition** section with: the table above, the split rationale, the risk rationale
(incl. why nothing is `low`), and the two exclusions above with their reasons. Append to **Findings &
Notes** only what this slice newly establishes — do **not** restate the harvested facts. New notes worth
recording:

- **The frozen baseline lands at `web/design/baseline/`** — beside the canvas mirror vocky already uses,
  inside `web/` so the `localDir: web/` mapping and Connect GitHub both reach it. (v12's canonical
  `docs/reference/design/baseline/` does not fit: vocky has no `docs/reference/` tree, and `docs/` is the
  versioned durable-truth machinery.) **Repo-only — not pushed as canvas cards**; the canvas is for live,
  re-themable cards, the baseline is the frozen "before".
- **`data-table` has no card but is the most-used primitive** (4 of 6 surfaces) and `intent.md` names it
  in the component list → `S2` adds it.
- **Baseline fidelity trap for `S1`:** the app self-hosts fonts via `next/font/google`, so a curl'd page
  references `/_next/static/media/*.woff2`, which dies with the server. Inlining only the stylesheet
  leaves the "frozen" render in system fonts. `S1` must resolve this (inline the faces, or record the
  gap explicitly) — a type change is one of the gate's two real questions, so font fidelity in the
  "before" is load-bearing.
- **The 6 surfaces are behind auth** — `S1`'s curl chain must POST login, keep the session cookie, and
  reuse it. `make smoke` / `src/vocky/smoke.py` already does signup → project → mint key → post
  feedback → poll read, so real data exists to render.
- **`S6` carries the one authorized `git push`** — ~340 files / +38k lines to the **public** repo,
  including all of `works/` and every verbatim operator message. `intent.md`: *"Worth one deliberate look
  before the gate slice runs."* Record it as an explicit `S6` obligation; **it is not a standing
  permission.**

## Mechanics and traps

- **`--depends-on` is `action="append"` — repeat the flag per dependency.** A comma-separated string is
  stored as one literal dep and fails `validate` with `missing dependency`. *(Found the hard way at the
  first `P8.DECOMP` — `phase.md` records it.)*
  ```
  python3 scripts/workflow.py new-slice --phase P8 --slice P8.S5 --name "..." \
    --kind implementation --risk high --order 5 \
    --depends-on P8.S2 --depends-on P8.S3 --depends-on P8.S4
  ```
- `--kind` and `--risk` are free-form strings (no `argparse` `choices`), so **`--kind co-work` is
  accepted** as the skill prescribes.
- **Create bare folders only.** Never pre-fill any middle slice's `plan.md` — the orchestrator writes
  each at that slice's own turn.
- This executor **never commits and never transitions slice/phase status**; it may run `new-slice`
  (this is a decomposition slice) and nothing else.

## Verification

- `python3 scripts/workflow.py validate` — must pass clean (catches the `depends_on` trap).
- `python3 scripts/workflow.py next` — must select `P8.S1`.
- `works/backlog.md` shows P8 with 7 middle slices at orders 1–7, `P8.S6` as `co-work`, none `low`.
- `phase.md`'s **Decomposition** section is filled; **Findings & Notes** gained only new facts.
