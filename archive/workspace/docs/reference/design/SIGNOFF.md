# Design SIGNOFF — vocky

_A factual record of each closed design gate. Newest round first._

---

## Round 02 — onboarding on the landing · gate closed 2026-07-29

**Phase:** P11 · **Slice:** P11.S5 · **Reviewer:** orchestrator-inline read-back (DesignSync)
**Design project:** `1eaa0803-46e3-426a-ab04-17a802170234` (`vocky design system`, verified by id —
the same project as round 01)

### Authorization — the operator's literal words

> "done"

The round's design decisions were concluded by the operator in the Claude Design session. The record
notes that the operator answered **"Decide for me" to all thirteen** of the handoff's §6 open questions,
delegating each to the session — so the decisions are Claude Design's, made under the operator's explicit
delegation, and each is recorded with its reasoning in `rounds/02-onboarding/output/result.md` §2.

### What this covers

Three onboarding surfaces the landing page did not have: a **hero install row** carrying
`curl -fsSL https://vocky.hi2vi.com/install.sh | bash`, an **agent quickstart** section built around the
two-variable contract (`VOCKY_BASE_URL` + `VOCKY_API_TOKEN`), and a **skill section** publishing
`/SKILL.md` for reading, copying, and download.

### What this supersedes

**Nothing.** Round 01's brand, tokens, and shipped components are unchanged, and no existing landing copy
or component was touched. This round is purely additive.

### Token delta

**None.** Every value resolves to an existing `@theme` token. The caution family (`--color-caution`,
`--color-caution-deep`, `--color-surface-caution`, `--color-hairline-caution`) was shipped in round 01 but
had no consumer; it now carries the trap treatment. The new vocabulary is **composition, not new tokens** —
three new components (`Snippet`, `Trap`, `SkillPreview`), specified in `output/build-prompt.md` §3.
`web/src/app/globals.css` requires **no change**.

### Record location & fidelity

- `rounds/02-onboarding/handoff.md` — what we asked for (OUT).
- `rounds/02-onboarding/output/{result.md, build-prompt.md}` — what Claude Design returned (IN), landed
  **verbatim and read-only**. **The build slices `P11.DECOMP2` cuts build from `build-prompt.md`.**
- **The card set stays in the design project** and is **not** copied down. The project now holds **43
  cards** — round 01's 30 plus **13 new** this round, across `Landing` (5), `Components` (4) and
  `States` (4). `_ds_manifest.json` compiled cleanly with counts in sync, so the round was genuinely
  visible in the Design System pane.
- `build-prompt.md` is self-sufficient by design: it carries every value, copy string, state, breakpoint
  and no-JS behaviour, because the executors that implement it have **no DesignSync**.

### Notes on this round's record

- **The round read the repo via a local-directory connection, not GitHub.** The handoff flagged that
  GitHub `main` was 45 commits behind local and that everything this round designs against was unpushed.
  No push happened and `ci.yml` did not fire.
- **A project-side path change, not a repo one:** round 01's `result.md` / `build-prompt.md` occupied the
  design project's `output/`, so the session copied them **unchanged** to `output/round-01/` before writing
  round 02 to the canonical `output/`. Nothing was edited or deleted, and **this repo's**
  `rounds/01-brand-app-landing/output/` is untouched.
- **Apply-time note (not a record edit):** `result.md` §6.4 logs that the handoff cited the skill as
  *119 lines, 7,975 bytes* while `wc -l` reports 120 (119 content lines + trailing newline).
  `build-prompt.md` §3.4 requires both figures be **computed from the served file, never hardcoded**, so
  the discrepancy cannot reach production.

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
