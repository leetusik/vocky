# Intent — P8

- Captured at: 2026-07-17T10:03:12+09:00
- Origin: operator

> **This phase has been re-shaped twice.** An earlier P8 ran under rules that did not yet exist and was
> reverted at `c9102e3`; the phase was re-created under workspace **v12**. Workspace **v13** then retired
> v12's seeded-canvas mechanism outright, so everything refined below was re-derived under v13's
> `design-cowork` skill. The operator's verbatim words are carried forward unchanged throughout
> (`git show 0007184:works/phases/active/P8/intent.md` for the first phase's copy).

## Original Input (verbatim)

> make a design system for the vocky app, and make a design co-work slice for that task. I'll finish the design system and acutall user interface with claude design.

Context — the operator's preceding message in the same exchange, which framed the request:

> let me ask you a question. p4.s1 said design system foundation did but I can't find one. where is it? I meant design system for actual claude designs design system we didn't do that right?

### Additional Operator Input (verbatim — 2026-07-17, at the first `P8.DECOMP` planning)

> for the design system, make a design system only for vocky but inherit hi2vi vibe.

### The process correction (verbatim — 2026-07-17, after the first `P8.S1`)

The single most load-bearing statement in this phase. It predates v12 by ~8 hours, and **v13 honors it
more literally than v12 ever did**: under v13 Claude Code authors nothing but a handoff.

> you don't understand the process. claude code will be nothing to do with the design. only claude design will do the design and after the design work, claude code(you) just use designsync skill to implement on this code base. you just make vocky's design system in claude design using dedicated skill, and wait till the design is done for the vocky app. and give me list of what to design.

### On implementation scope (verbatim)

> not just re-skinning. there maybe feature change while re-design process.

### The v12 re-scope request (verbatim — 2026-07-17, the phase's re-creation)

> p8 is working phase but not match with new arrived v12 rule. revertwhat we've done for p8, and fresh start the design part again. with changed rule

### The v13 re-scope request (verbatim — 2026-07-17, this revision)

> and revise p8 according to new design rule.

> well, remove previous stuff. we gonna do fresh start

## Confirmed Intent (refined + clarified)

Run vocky's **real Claude design gate** — the one P4 deliberately deferred (**D-P4-3**) — under
workspace v13's `design-cowork` rules. **This phase is the design only; the implementation is P9.**

**Why this phase exists.** P4.S1 shipped the design-system *mechanism* only: the Tailwind v4 `@theme`
token block in `web/src/app/globals.css` and the CVA primitives in `web/src/components/ui/`. Its
**values** are a deliberately neutral placeholder set — a slate surface ramp plus one indigo accent —
reusing hi2vi_web's token *names* verbatim so a later gate could swap values only (hence `--color-green`
is currently indigo `#6366f1`). **No vocky brand exists yet.** This phase supersedes **D-P4-3**, which
deferred the intensive operator design session to P6.

**Mechanism — v13: write the handoff, STOP, read back, land.** Claude Design **reads the real repo
itself** (the operator runs **Connect GitHub**), so Claude Code authors **no cards, no canvas, no token
mirror** — a mirror only drifts, and the repo is already the truth. Claude Code's **one output is
`handoff.md`**: product context, the scope checklist, locked vs. in-play, where to look, the required-
output manifest, and the open questions posed back. It then **STOPS** (`pending`), reads the result back
with the `DesignSync` tool (**read-back only**), runs the concreteness check, lands the design **as-is**,
and writes the `SIGNOFF`. P9 implements.

- Live target: claude.ai design-system project **`1eaa0803-46e3-426a-ab04-17a802170234`**
  (`vocky design system`, `PROJECT_TYPE_DESIGN_SYSTEM`, verified). **Nothing was ever pushed to it.**
  **Target by id, never by name** — a second project shares the name, and `list_projects` can return one
  the operator's UI does not show. Confirm against the operator's screen at the gate, not the API.
- **`/design-sync` is never run here** — it is a repo→component-bundle compiler, a different thing, and
  is not this workflow. It was tried here off-book and failed; see `phase.md` → *Constraints*.

**Division of labor — the load-bearing constraint.** The agent's scope is **the handoff only, with zero
brand decisions.** Every brand decision is concluded **in the operator's Claude Design session, with
Claude Design asking the operator those questions.** The agent does not propose a palette, a type
direction, or a brand — and never answers a design question; it poses it back.

**The line** (v13, and the operator's own ruling): *documenting what exists is Claude Code's job;
deciding what it should look like is Claude Design's.* Describing the live palette in the handoff is
documentation. Proposing a palette is design — not ours.

**One session covers app + landing together:**

- Foundations — colors, type, spacing/radius.
- Components — `button`, `card`, `badge`, `field`, `grid`, `section`, `data-table`.
- App sections — login/signup, app shell, dashboard, project detail, feedback list, feedback detail
  (every surface P4.S2–S5 shipped).
- Landing sections — hero, features, pricing, footer.

**Landing copy is not drafted by the agent.** Claude Design surfaces the value-prop and messaging
questions during the session, and the returned record carries the real copy back.

**Implementation is a floor, not a ceiling — and it is P9.** Per the operator: *"not just re-skinning.
there maybe feature change while re-design process."* P9's slices follow the signoff wherever it lands
— token/palette swap, primitive changes, app surface rework, the landing build, **and any feature or
UX changes the session concludes on**, including backend if required. **The phase's true size stays
unknown until the signoff; that is accepted**, and is why P9 is a separate phase whose `DECOMP` runs
only after this gate closes.

## Clarifications Resolved

Carried forward from the first P8 (still binding):

- Q: Where should the design co-work slice live — inserted into P4, a new phase, or P6? — A: A new
  phase before P5, and it includes the real implementation. (→ order `4.5`, following P7's
  fractional-insert precedent at 3.5.)
- Q: How far should the agent take the design system before handing off — with no brand decisions, or a
  first-cut brand proposal to refine? — A: **No brand decisions**; "the brand decisions will be
  concluded with the claude design. by it asking me those."
- Q: Which surfaces are in scope — app only, or app + landing? — A: **App + landing together**, in one
  session. This absorbs P6's design work.
- Q: Does "include real implementation" cover building the landing page too, or just re-skinning the
  app? — A: **Everything**, "and not just re-skinning. there maybe feature change while re-design
  process."
- Q: The landing page has no copy or value prop written yet — where does that come from? — A: Claude
  Design asks the operator during the session; the handoff poses it as an open question.
- Q: P8 absorbs P6's landing design and landing build — should P6 be re-scoped now? — A: **No.** Note
  the consequence here; leave P6 untouched and reconcile at `P6.DECOMP`.
- Q: The app-section list says "login, tenant dashboard, project detail, usage" but never names the
  feedback list/detail that P4.S5 shipped — how much coverage? — A: **Every shipped surface**
  (login/signup, app shell, dashboard, project detail, feedback list, feedback detail).
- Q: If the design session concludes on feature/UX changes, does that reopen the P2/P3 API contracts
  or stay frontend-only? — A: **Backend in scope if needed.** The phase may reopen `src/vocky/**` and
  the P2/P3 contracts to serve what the design concludes.
- Q: "Inherit hi2vi vibe" collides with "zero brand decisions" — how does the vibe reach the session
  without the agent deciding vocky's brand? — A: **A clearly labeled `REFERENCE — hi2vi vibe` section
  in the handoff**, showing hi2vi's real palette/type beside vocky's current values, so Claude Design
  can ask the operator how far to carry it. The claude.ai project stays **vocky-only** otherwise. (v13
  prescribes exactly this: any operator-named reference goes in *"clearly labeled REFERENCE — data, not
  a proposal."*)
- Q: Must P4.REVIEW close before this phase starts? — A: Yes, and it has — `P4.REVIEW` passed at
  commit `8cea96f`.

### Resolved at the v12 re-creation (2026-07-17)

- Q: How deep should the revert go? — A: **Full revert of P8**; re-create the phase fresh. (Done at
  `c9102e3`.)
- Q: The claude.ai project holds a half-pushed bundle — reuse it or start fresh? — A: **Fresh project;
  abandon the current one.** The operator's Design systems UI does **not** show `2d64ae63-…` even though
  `list_projects` returns it — and an invisible project cannot host a design gate. *(Claude Code
  initially argued to reuse it, on the strength of `list_projects`. The operator's screen was right; the
  API and the UI disagreed.)* DesignSync has **no `delete_project`**, so the old shell persists forever.
  **Both projects are named `vocky design system`; target by id, never by name.**
- Q: A big design change → two phases. One phase or two? — A: **Two.** P8 = design (order 4.5),
  **P9 = apply (order 4.6)**. Both still land before P5@5, so the operator's original "a new phase
  before P5, and it includes the real implementation" ruling holds on both clauses: the implementation
  happens in this stream, ordered before P5, rather than being deferred a third time. **v13 keeps this
  shape** — a big design gets a design phase, then an apply phase.
- Q: Connect GitHub needs `main` on origin — but `main` is ahead and the repo is public. — A: **Push,
  then Connect GitHub.** v13 authorizes exactly this one push, **at the design slice only** — *"it is
  not standing permission."* See the Notes for what that publishes.

### Resolved at the v13 revision (2026-07-17)

- Q: v13 retires the seeded canvas — what happens to `web/design/canvas/`? — A: **Retire it.** The
  13-file mirror (`tokens.css`, `_ds_manifest.json`, 10 cards, `README.md`) has no job under v13: Claude
  Design reads the repo directly, and a mirror can only drift. **P8 deletes it** as a slice, and
  `P8.REVIEW` re-versions `frontend.md`, which documents its structure and card count. It is inert today
  — nothing in the app or the build imports it — and git history keeps it.
- Q: Where does the design record live, now that the canvas arm is gone? — A: **`docs/reference/design/`**
  — v13's canonical layout, and it does not exist yet. Outside `works/` on purpose: **P8 archives before
  P9 runs**, so a record inside `works/` would move out from under the phase that needs it.
- Q: How much of the v12-era phase text survives? — A: **Fresh v13 docs, keep the measurements.** The
  verbatim operator inputs (immutable), the harvested codebase facts, and the open questions carry
  forward; everything naming the retired mechanism — seed, canvas, cards, `@dsCard`, the frozen baseline
  render, the re-push obligation, the manifest, the `/design-sync` correction, and *"why P8 exists
  twice"* — is dropped. Git history keeps all of it.

## Notes

- **The design slice must be `--kind co-work --risk high`, and is NEVER dispatched.** v13's deliberate
  exception to the contract's "every slice is delegated": executors have no `DesignSync` tool, so the
  read-back is **orchestrator-inline**. Never rate a design slice `low`.
- **A design slice never writes implementation code.** It ends at the landed design + SIGNOFF. Landing
  the design is not implementing it — it is what makes P9 easy.
- **Do not over-plan before the gate.** v13: *"you do not know what the operator will design."* `DECOMP`
  creates round 1 only. If the session needs a round 2, cut it at a fractional order afterward; *"expect
  the read-back to re-shape the phase."*
- **The one authorized `git push`** publishes to the **public** `github.com/leetusik/vocky`, including
  all of `works/` — every phase notebook and every verbatim operator message in this file. **No secrets
  travel** (verified: `.env` is gitignored, `web/.env.local` matches `web/.gitignore:4 .env*.local`, only
  `*.env.example` are tracked). `.claude/settings.json` denies `Bash(git push:*)`, so the operator
  approves that one push at the gate. Worth one deliberate look before the design slice runs. *(v13
  offers a local-dir connection as the no-push alternative; vocky's repo is already public, so Connect
  GitHub stands.)*
- **P6 consequence (deliberately not yet applied).** P8+P9 absorb both the landing *design* and the
  landing *build*, which leaves **P6 as production-deploy-only** (vocky.hi2vi.com, the oracle-cloud
  box, nginx via edge). P6's name, objective, and `intent.md` are **intentionally untouched** — the
  operator chose to reconcile them at **P6.DECOMP**. P6's intent still reads "landing page + deploy"
  and still claims the design-gate workflow; that is known and stale, not an oversight.
- **The `/` design-system preview page is gone.** P4.S2 replaced P4.S1's preview at
  `web/src/app/page.tsx` with a session redirect. Under v13 that no longer matters — Claude Design reads
  the source, not a rendered preview.
- All measured findings and the open gate questions live in [phase.md](phase.md) → *Findings & Notes*.
  **Do not re-derive them.**
