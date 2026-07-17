# P9.REVIEW — Plan: phase review + durable-doc consolidation

## Context — why this slice exists

The single review gate for the whole P9 apply. All seven middle slices are `done` and committed
(`fd0411d` S1 … `1e271bd` S7). This slice validates the phase's work **together**, reviews it against the
objective / `intent.md` / the design contract, and — **only on a passing review** — consolidates the
accumulated `phase.md` **Doc impact** notes into new durable-doc versions. Delegated to
`slice-executor-high` (fresh, independent context); the executor returns a `review_verdict` and the
orchestrator records it via `review-phase`.

## What the review executor does

### 1. Consolidated validation (all slices at once)
- `cd web && pnpm typecheck && pnpm lint && pnpm build && pnpm test` — all green (S7 confirmed; re-run as the
  phase-level gate).
- `python3 scripts/workflow.py validate` — state integrity.
- Grep-assert the phase's negative-space invariants still hold: zero `min-[900px]:`, zero `--breakpoint-xs`,
  no `inputVariants()`-template `<select>`, no old variant names, `content/nav.ts` gone.

### 2. Review against objective / intent / DoD (read, don't re-implement)
Read the phase objective (`phase.json`), `intent.md` (esp. **RESPECT THE DESIGN**, "faithful apply", the
expected shape: foundation → net-new isolated → fidelity fix → sweep), the whole `phase.md` notebook, each
slice's `result.md`, and `build-prompt.md §10` (the DoD). Confirm:
- Every designed element shipped — **nothing dropped, simplified, or "improved"** (the load-bearing rule).
  The one deliberate omission (feedback-list **optional** removable filter-chips) is **spec-sanctioned**
  (`build-prompt §5/§4.9` marks it optional; the page's no-client-island design is preserved) — not a drift.
- All 12 DoD §10 items hold; all locked floors intact (identical login error, 404-never-403, show-once key,
  download-only attachments, UTC, `word-break: keep-all`, Korean-capable `--font-sans`, `FieldError`
  `aria-live`, distinct empty states).
- **No backend / `src/vocky/**` / contract change** (§9) — confirm the diff is web-only + docs + `works/`.

### 3. Verdict
Return `review_verdict`: **pass** (objective met, DoD holds, floors intact) · **changes_requested** (with a
concrete fix list) · **blocked** (an impediment). Note the 13 pre-existing P4-era `format:check` failures as
**known pre-existing debt** (P9 introduced none) — **not** a review blocker.

### 4. On PASS ONLY — consolidate docs (the executor may run `doc-new-version` in the review slice)
Consolidate the `phase.md` Doc-impact notes into new versions (writing **only docs, never source**):
- **`frontend` v0003 → v0004** — the applied vocky design: deep-emerald palette (value swap, names kept),
  compact type/radius/spacing scale, Pretendard loader, the new component vocabulary (Select, Chip,
  destructive/destructiveOutline/ghost Button, split Badge, folded LogoutButton, dependency-free area
  TrendChart), `--breakpoint-app` (and `--breakpoint-xs`/`min-[900px]:` retired), the four net-new states,
  the public `/` landing, and the retired `design/canvas` + `nav` leftovers. **Flip the "placeholder
  still-live" language to "applied."**
- **`experience` v0006 → v0007** — the public landing now serves `/` to signed-out visitors (signed-in bounce
  preserved) as a real product surface.
- **`decisions`** — `D-P8-1` is now **applied** by P9 (not superseded). Add a version **only if** it records
  durable truth beyond a status note (executor's judgment); otherwise leave `v0006` (the decision stands).
- **No new version** for backend/data/security/api/architecture/product/operations — §9: no contract/backend
  change, and the security floors were preserved, already documented (`security` v0005).
- Then `python3 scripts/workflow.py rebuild-docs` to regenerate `docs/current/*`.

### 5. Return — do NOT transition phase/slice status
The executor returns the `review_verdict` + the doc-version summary. It does **not** run `review-phase`,
`finish-slice`, or commit — those are the orchestrator's.

## Boundary

- The review **writes only docs** (new versions under `docs/versions/*` via `doc-new-version` + `rebuild-docs`)
  — never source, never `works/` state transitions.
- On `changes_requested`/`blocked`, **do not consolidate docs** — docs are versioned once, on a pass.

## After the executor returns (orchestrator, not this slice)

- Record: `python3 scripts/workflow.py review-phase P9 --verdict <pass|changes_requested|blocked> --reviewer slice-executor-high --note "…"` → this sets the phase `done` + closes the `REVIEW` slice on a pass (no separate `finish-slice`).
- `python3 scripts/workflow.py validate`, then commit (`docs(P9.REVIEW): …`).
- On `changes_requested`: create the executor's proposed `P9.Fn` fix slices, run them, re-review.
- A pass leaves P9 `done` in `active/` — **do not archive** (a separate manual step).

## Verification

- `review-phase` recorded; `validate` clean; `docs/current/frontend.md` (+ `experience.md`, ± `decisions.md`)
  regenerated to the new versions; `git status` shows only docs + `works/` changes from this slice.
