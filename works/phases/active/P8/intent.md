# Intent — P8

- Captured at: 2026-07-16T23:16:33+09:00
- Origin: operator

## Original Input (verbatim)

> make a design system for the vocky app, and make a design co-work slice for that task. I'll finish the design system and acutall user interface with claude design.

Context — the operator's preceding message in the same exchange, which framed the request:

> let me ask you a question. p4.s1 said design system foundation did but I can't find one. where is it? I meant design system for actual claude designs design system we didn't do that right?

## Confirmed Intent (refined + clarified)

Run vocky's **real Claude design gate** — the one P4 deliberately deferred — and implement its
outcome across the app and the landing page.

**Why this phase exists.** P4.S1 shipped the design-system *mechanism* only: the Tailwind v4
`@theme` token block in `web/src/app/globals.css`, the CVA primitives in
`web/src/components/ui/`, and the `web/design/canvas/` browser-openable mirror. Its **values** are
a deliberately neutral placeholder set — a slate surface ramp plus one indigo accent — reusing
hi2vi_web's token *names* verbatim so a later gate could swap values only (hence `--color-green` is
currently indigo `#6366f1`). **No vocky brand exists yet.** This phase supersedes **D-P4-3**
(`works/phases/active/P4/phase.md`), which deferred the intensive operator design session to P6.

**Mechanism.** The gate is a claude.ai/design design-system project synced via the `DesignSync`
tool + the `/design-sync` skill, closing with a `SIGNOFF.md` dropped on the canvas — the same
workflow hi2vi_web ran at P14.S1 (see `~/projects/personal/hi2vi_web/design/canvas/P14.S1-SIGNOFF.md`
for the precedent and the read-back convention).

**Division of labor — the load-bearing constraint.** The agent's scope is **canvas prep only, with
zero brand decisions.** Build faithful canvas cards mirroring the *real shipped surfaces* at the
current placeholder palette, push them to a claude.ai design-system project, and hand off. Every
brand decision is concluded **in the operator's Claude Design session, with Claude Design asking the
operator those questions.** The agent does not propose a palette, type direction, or brand.

**One session covers app + landing together:**

- Foundations — colors, type, spacing/radius.
- Components — `button`, `card`, `badge`, `field`, `grid`, `section`, `data-table`.
- App sections — login, tenant dashboard, project detail, usage (the surfaces P4.S2–S5 shipped).
- Landing sections — hero, features, pricing, footer.

**Landing copy is not drafted by the agent.** The landing cards ship with placeholder copy slots;
Claude Design surfaces the value-prop and messaging questions during the session, and the `SIGNOFF`
carries the real copy back.

**Implementation is in scope, and it is a floor rather than a ceiling.** Per the operator: *"not
just re-skinning. there maybe feature change while re-design process."* The implementation slices
follow the signoff wherever it lands — token/palette swap, primitive changes, app surface rework,
the landing page build, **and any feature or UX changes the design session concludes on.** Scope the
implementation slices from the signed-off design, not from a presumed visual-only diff.

## Clarifications Resolved

- Q: Where should the design co-work slice live — inserted into P4, a new phase, or P6? — A: A new
  phase before P5, and it includes the real implementation. (→ P8 at `--order 4.5`, following P7's
  fractional-insert precedent at 3.5.)
- Q: How far should the agent take the design system before handing off — canvas prep with no brand
  decisions, or a first-cut brand proposal to refine? — A: Canvas prep only; "the brand decisions
  will be concluded with the claude design. by it asking me those."
- Q: Which surfaces go on the canvas — app only, or app + landing? — A: App + landing together, in
  one session. This absorbs P6's design work.
- Q: Does "include real implementation" cover building the landing page too, or just re-skinning the
  app? — A: Everything, "and not just re-skinning. there maybe feature change while re-design
  process."
- Q: The landing page has no copy or value prop written yet — where does that come from? — A: Claude
  Design asks the operator during the session; cards ship with placeholder copy.
- Q: P8 absorbs P6's landing design and landing build — should P6 be re-scoped now? — A: No. Note
  the consequence in P8's intent; leave P6 untouched and reconcile at P6.DECOMP.

## Notes

- **P6 consequence (deliberately not yet applied).** P8 absorbs both the landing *design* and the
  landing *build*, which leaves **P6 as production-deploy-only** (vocky.hi2vi.com, the oracle-cloud
  box, nginx via edge). P6's name, objective, and `intent.md` are **intentionally untouched** — the
  operator chose to reconcile them at **P6.DECOMP** rather than rewrite a downstream phase now.
  P6's intent still reads "landing page + deploy" and still claims the design-gate workflow; that is
  known and stale, not an oversight.
- **P4.REVIEW is outstanding.** P4 should close on its functional merit before P8 starts, since P8
  reworks what P4 built. P4's `phase.json` still reads `planned` despite S1–S5 being done.
- **The existing canvas is a scaffold, not a baseline.** `web/design/canvas/` currently holds
  `tokens.css` (a 1:1 `:root` mirror of the app's `@theme`), `_ds_manifest.json` (namespace
  `VockyDesignSystem_<short>`, 125 tokens, 10 cards), foundations + component cards, and a single
  `sections/dashboard-placeholder.html`. **No card mirrors a real shipped surface** — the app grew
  login, dashboard, project detail, and usage in S2–S5 while the canvas stood still. Card-vs-surface
  drift is the prep work, not a bug to fix in passing.
- **`data-table` has no component card.** It is net-new in P4.S1 and is currently previewed only
  inside `sections/dashboard-placeholder.html`.
- **Canvas ↔ app sync is manual and bidirectional-by-hand.** `globals.css`'s `@theme` is the source
  of truth for the running app; `canvas/tokens.css` mirrors it. The signoff read-back must edit both
  in lockstep (see `web/design/canvas/README.md`).
- **No dark mode.** The app uses explicit surface tokens with no `.dark` block and no theme toggle
  (P4 decision). Worth an explicit answer at the gate rather than an accident.
- **The `/` design-system preview page is gone.** P4.S2 replaced S1's preview at
  `web/src/app/page.tsx` with a session redirect, so today the canvas HTML files are the only way to
  view the system.

## Open Questions

- Does the canvas push to a **new** claude.ai design-system project, or an existing one? (`DesignSync
  list_projects` at DECOMP; note the target must be `type: PROJECT_TYPE_DESIGN_SYSTEM`, which is
  immutable at creation.)
- Must **P4.REVIEW** close before this phase starts?
- If the design session concludes on **feature/UX changes**, how much of the app's feature surface is
  in play — and does that reopen P2/P3 API contracts, or stay frontend-only?
