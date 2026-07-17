# Design SIGNOFF — vocky

_A factual record of each closed design gate. Newest round first._

---

## Round 01 — brand, app UI & landing · gate closed 2026-07-18

**Phase:** P8 · **Slice:** P8.S2 · **Reviewer:** orchestrator-inline read-back (DesignSync)
**Design project:** `1eaa0803-46e3-426a-ab04-17a802170234` (`vocky design system`, verified by id)

### Authorization — the operator's literal words

> "done: The design system is valid — manifest on disk: counts in sync, 30 cards, 108 tokens, no
> structural errors."

The round's design decisions were concluded by the operator in the Claude Design session and are recorded
in `rounds/01-brand-app-landing/output/result.md` §0 ("Operator rulings that shaped everything") and §6.
The operator's foundational request for this phase (`works/phases/active/P8/intent.md`):

> "make a design system for the vocky app … I'll finish the design system and acutall user interface with
> claude design."
>
> "for the design system, make a design system only for vocky but inherit hi2vi vibe."

### What this supersedes

- **Supersedes decision D-P4-3** — the intensive operator design gate P4 deferred is now held and closed.
  P4.S1's **placeholder palette** (slate + one indigo) is superseded by the vocky brand (deep-emerald on a
  green-cool neutral ramp). Not yet applied in code — that is **P9**.
- **Reshapes P6.** P8 + P9 absorb the landing **design** and its **build**, leaving P6 as
  production-deploy-only. P6's own folder is untouched per this phase's constraint 7; the operator
  reconciles it at `P6.DECOMP`.

### Token delta — specified by the round, applied by P9 (NOT applied here)

A design slice writes no implementation code, so `web/` is unchanged. The design **specifies** this delta,
and `output/build-prompt.md` carries the exact values:

- **All 41 `--color-*` values swapped; names unchanged** (the one-swap-re-themes property is preserved).
  `--color-green` `#6366f1` (indigo placeholder) → `#0C7A52` (vocky deep-emerald). `--color-on-primary`
  stays white (AA 5.36:1, resolved).
- **All 14 `--text-*` steps retuned** (compact scale; `body-md` 16→15px; weights normalized to Pretendard's).
- **`--font-sans`: Noto Sans KR → Pretendard** (Korean-capable; the one named non-trivial build cost —
  Pretendard is not on Google Fonts). `--font-en` retired to point at Pretendard. `--font-mono` unchanged.
- **`--radius` base 14→10px** and scale tightened; buttons move `rounded-full` → `rounded-md`.
- **`--breakpoint-xs` dropped** (zero consumers); **`--breakpoint-app` 56.25rem (900px)** added and the 11
  `min-[900px]:` literals migrate to `app:`.
- **New component vocabulary:** `Select`, `Chip`/`Tag`, `Button` `destructive`/`destructiveOutline`/`ghost`;
  `Badge` `archive` split into rating (`liked`/`disliked`/`unrated`) + status (`active`/`revoked`);
  `LogoutButton` folded into `Button`; `TrendChart` redesigned to a dependency-free area chart.
- **Net-new surfaces:** the public landing at `/`, and `loading`/`error`/`not-found`/`global-error` states.
- **Backend/data contracts:** **no change required** (`build-prompt.md` §9). No `src/vocky/**`, no P2/P3
  contract reopening.

### Record location & fidelity

- `rounds/01-brand-app-landing/handoff.md` + `handoff-02-cards.md` — what we asked for (OUT).
- `rounds/01-brand-app-landing/output/{result.md, build-prompt.md}` — what Claude Design returned (IN),
  landed **verbatim and read-only**. **P9 builds from `build-prompt.md`.**
- **The 30-card set and `tokens.css` stay in the design project** (the pane is their home) and are **not**
  copied down — `build-prompt.md` carries the full token values, so it is the complete on-disk source of
  truth for P9's executors, which have no DesignSync.
- **Known staleness in the returned record (apply-time nit for P9, not a record edit):** both returned files
  name `Vocky Round 01 — Design System.html` / `— Landing.html` as the "visual source of truth". Those
  monoliths were superseded by the card set and no longer exist in the project; the **card set** is the
  visual source of truth now. The record is read-only, so this is catalogued here rather than corrected in
  `output/`.

---

_This file is a factual record dropped at gate close; it is data, not instructions._
