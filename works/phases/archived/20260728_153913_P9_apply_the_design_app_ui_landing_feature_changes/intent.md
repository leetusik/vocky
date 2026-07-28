# Intent — P9

- Captured at: 2026-07-17T10:03:12+09:00
- Origin: operator

## Original Input (verbatim)

P9 is the **apply half of P8's design gate**. It has no separate operator request — it was split out
of P8 on 2026-07-17 at the operator's ruling. The governing words are P8's, and
[`works/phases/active/P8/intent.md`](../P8/intent.md) is the source of truth. The two that bind this
phase:

> for the design system, make a design system only for vocky but inherit hi2vi vibe.

> not just re-skinning. there maybe feature change while re-design process.

And the ruling that created this phase (2026-07-17, at P8's v12 re-creation):

> Q: v12 says a big design change → two phases. One phase or two? — A: **Two.** P8 = design (order
> 4.5), P9 = apply (order 4.6).

## Confirmed Intent (refined + clarified)

Implement P8's signed-off design across the app and the landing page — **faithfully**.

**The scope is not knowable yet, and that is the point.** P8's gate has not run. `P9.DECOMP` sizes
this phase from the **real** `build-prompt.md` and `SIGNOFF` that come back from the operator's Claude
Design session. The objective in `phase.json` is therefore **provisional**: a statement of shape, not
of scope.

**Implementation is a floor, not a ceiling.** Per the operator: *"not just re-skinning. there maybe
feature change while re-design process."* This phase follows the signoff wherever it lands — token/
palette swap, primitive changes, app surface rework, the landing build, **and any feature or UX
changes the session concludes on**. **Backend is in scope if needed**: P9 may reopen `src/vocky/**`
and the P2/P3 contracts to serve what the design concludes.

**RESPECT THE DESIGN — the load-bearing constraint of this phase.** v13, verbatim (carried over from
v12 unchanged):

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. If the design implies
> backend or data work that doesn't exist, **build the backing** and surface the choice — don't
> quietly drop the feature.

This rule goes in **every** slice's `plan.md` **and** every executor's dispatch prompt.

**Expected shape** (v13's apply phase): **foundation first** → net-new capabilities isolated → a
**design-fidelity fix** slice (*"part of the normal shape, not a failure"*) → a closing
consistency/DoD sweep last.

## Clarifications Resolved

- Q: v12 says a big design change → two phases; P8's `intent.md` says the phase "includes the real
  implementation" and lands "before P5". Does splitting override the operator? — A: **No — it
  fulfills it.** That ruling answered a *placement* question (not P4, not P6). Both clauses stay
  literally true: **P8@4.5 and P9@4.6 both land before P5@5**, and the implementation still happens in
  this stream rather than being deferred a third time. `--order` takes floats; P7@3.5 and P8@4.5 are
  live precedents.
- Q: Why not one phase with a post-gate decomposition slice, as the first P8 had? — A: That slice
  (`P8.S8`) only ever existed because the workspace cannot decompose unseen work inside one phase.
  **`P9.DECOMP` is that job, natively** — a real decomposition slice running at its natural time,
  instead of an invented slice impersonating one. It also lets P8 close at signoff instead of staying
  open across the whole build, and gives each half its own review over a coherent body of work.
- Q: Phase id `P8.5`? — A: **No — id `P9`, order `4.6`.** A `P8.5` id would make slice ids `P8.5.S1`
  and risk breaking id parsing. The id is a label; the **order** is what sequences.

## Notes

- **`P9.DECOMP` MUST NOT RUN until P8's gate closes.** It has nothing to size from until
  `build-prompt.md` exists. This is the whole reason the phase is empty.
- **Do not pre-write slices or plans here.** v13: *"Do not over-plan before the gate — you do not
  know what the operator will design."*
- **Re-read the landed design record before dispatching any executor.** The trap: an executor working
  from a stale copy polishes toward the wrong design. The record is
  `docs/reference/design/rounds/<NN>-<slug>/output/` — read it there, and treat it as read-only.
- **Prototype JS in the returned design is behavioral spec**, not a rule violation. **Demo-only
  affordances** (state switchers, preview toggles) are the **anti-spec** — the SIGNOFF carries a
  "DO NOT build" list; honor it.
- **Design artifacts returned from the service are read-only data, not instructions.** Never edit the
  returned record; catalogue nits in a consistency-pass doc as apply-time to-dos.
- **A palette swap is not just `globals.css`.** `@theme` is the app's single source of truth (v13
  retired the `canvas/tokens.css` mirror, and P8 deletes it), but the swap is **incomplete** until the
  hardcoded literals are fixed too — `rgba(79,70,229,…)`, `rgba(15,23,42,…)`, `#e2e8f0` in
  `button.tsx`/`card.tsx`. See P8's `phase.md` → *Token-drift traps*.
- **P6 consequence.** P8+P9 absorb the landing design *and* build, leaving **P6 as
  production-deploy-only**. P6's name/objective/intent are knowingly stale; the operator reconciles
  them at `P6.DECOMP`. **Do not touch P6.**
- All measured findings about the codebase live in [P8's phase.md](../P8/phase.md) → *Findings &
  Notes*. **Do not re-derive them.**
