# P11.S10 — Design-fidelity pass: acceptance checks, no-JS, a11y and reduced-motion floors

> ## RESPECT THE DESIGN
> **Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
> failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
> intent, never a plainer fallback.**

## What this slice is

The last build slice. `design-cowork` treats a fidelity pass as **part of the normal shape, not a failure**.
Its job is to run `build-prompt.md` §11's seven acceptance checks across the whole round, verify the §8 and
§9 floors that no single earlier slice was positioned to check end-to-end, adjudicate the one open
question S8 and S9 both deferred, and fix what fails.

Source of truth: `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` **§7, §8, §9, §11**.
Read `works/phases/active/P11/phase.md`'s "S6 done" through "S9 done" notes — they record exactly what each
slice left for you.

**Bias: verify first, change little.** Corrections 9 and the S6–S9 results suggest most floors already
hold. A fidelity pass that rewrites working code is a worse outcome than one that proves it correct. Every
change you do make must be justified against the spec, in `result.md`.

## 1. The seven acceptance checks — §11

Run each, record the verbatim evidence, and fix genuine failures.

1. **The install command pastes as one unbroken line from any width.** The floor is `whitespace-pre` +
   `overflow-x-auto` and a clipboard that reads the node's `textContent`. Verify on the hero row *and* the
   quickstart's step 1.
2. **The preview's line and byte counts change automatically when the skill changes.** S9 already probed
   this (119/7975 → 120/8029 → restored). **Re-run it** — it is the check that proves neither a hardcode
   nor a forked excerpt crept back in. **Restore `web/public/SKILL.md` afterwards and confirm
   `python3 scripts/skill_parity.py` is `PASS`.**
3. **With JS disabled: no copy button anywhere, the pane still shows the file and scrolls, and
   `Download SKILL.md` downloads it.** S6, S8 and S9 each added `renderToStaticMarkup` assertions. Verify
   the *composite*: render the **whole page** (or `next start` + fetch `/`) and assert that the only
   `<button` in the document is P9's pre-existing disabled Pricing CTA — S9 confirmed that is the sole
   legitimate one. This is the check no earlier slice could make alone.
4. **Zero literal copy in the new components.** `grep` every file the round added under
   `web/src/components/landing/` and `web/src/components/ui/` for prose string literals. Everything must
   come from `LANDING`.
5. **No `vk_live_` anywhere; no flat `source_product`; the hero payload diff is empty.**
   **Scope this correctly** (S7's finding): three read-only S5 design-record files under
   `docs/reference/design/` contain `vk_live_` in *negation* form, documenting the correction. Those are
   expected and permanent. Restrict the check to `web/` and `src/`, and say so.
6. **The trap block has no `role="alert"` and no `aria-live`.**
7. **The nav has exactly five links, and `#quickstart` and `#skill` both scroll to their sections.**
   Confirm the order is `How it works · Get started · Features · Pricing · Docs`.

## 2. The open question you must adjudicate — `Section` padding

**Both S8 and S9 chose `Section`'s shipped default** (`py-section` / `md:py-section-lg` = 72/104px) over
§5/§6's explicit `Padding 84px 28px`, and both were asked to record the argument rather than just the
choice. Decide it here, once, for both sections.

The case for the default, as S9 put it:

- **`28px` is not the landing's gutter.** The page uses `px-5 md:px-14`, so taking the literal horizontal
  value would visibly misalign these two sections' edges from every neighbour.
- **`84px` is not on the shipped spacing scale**, and §1 forbids adding or renaming a token.
- §6's other explicit value — **container `1180px` — is honoured exactly.**

The case against: **correction 5 established that explicit values are normative and descriptive labels are
not**, and RESPECT THE DESIGN forbids choosing a plainer fallback to save effort.

Weigh them and decide. Two constraints on the outcome:

- **Whatever you decide applies to both sections identically** — they are siblings and a split would be
  visibly wrong.
- **If you keep the default, say plainly in `result.md` that this is a deliberate, argued departure from
  two explicit values in the contract**, so the phase review sees it as a decision rather than an
  oversight. If you change it, do it without touching `globals.css` or adding a token.

## 3. The §9 a11y floor — verify, don't rebuild

Correction 9 established that **both relevant floors are already global CSS**:
`globals.css:276-279` ships `:focus-visible { outline: 2px solid var(--color-green-deep); outline-offset: 2px }`,
and `:282-291` already forces near-instant transitions under `prefers-reduced-motion: reduce`.

So these are **verifications, not implementations** — and neither needs the `globals.css` change §10
forbids:

- Every new button and anchor receives the focus ring.
- **Both scrollers are focusable (`tabIndex={0}`)** so they can receive it and be keyboard-scrollable —
  §9 requires this explicitly. Check the preview body and any other `overflow-auto` region the round added.
- Both new sections are `<section>` with an `<h2>`; the quickstart's steps are semantically an ordered list.
- The status chips repeat their literal code, and the trap carries the word "trap" — **colour is never the
  sole carrier of meaning.**
- Nothing in the round interrupts a screen reader on load: no `role="alert"`, no assertive live region.
  The copy buttons' success announcements are **polite**.

## 4. The §7 state table and §8 no-JS floor

Verify against the normative table:

- Copy **success reverts after 2000ms**; copy **failure persists** until the next attempt and
  **programmatically selects** the command text with the shortcut hint. That asymmetry is deliberate.
- Preview collapsed 380px + fade / expanded 640px, still a scroller, **never unbounded**; narrow 300/480px.
- No-JS: copy buttons **absent, not inert**; the pane scrolls; the footer uses the no-JS string and offers
  the raw file; `Download SKILL.md` works.

The clipboard states cannot be exercised without a DOM — there is **no jsdom in this repo**. Verify them by
**reading the code against the table** and say so plainly; do not add a browser test runner for this slice.

## 5. Whole-round consistency

A few things only a cross-cutting pass can catch:

- The install command string is **identical** in `web/public/install.sh`'s header, `docs/cli.md`,
  `README.md`, the hero row and quickstart step 1. `grep` it and compare.
- `page.tsx`'s final section order matches §2: Hero · TrustStrip · HowItWorks · **AgentQuickstart** ·
  **SkillSection** · Showcase · Features · Pricing · ClosingCTA.
- `section-ids.ts` has exactly the five ids in use and no orphan.
- The two new sections' `tone` values match §2 (`default` then `surfaceSoft`) so the tonal ramp alternates.

## Validation

From `web/` unless noted:

1. `pnpm typecheck` → exit 0.
2. `pnpm lint` → exit 0.
3. `pnpm test` → all **78** pass, plus anything you add.
4. `pnpm build` → succeeds, **zero warnings** (S9 left it warning-free — keep it that way), `/` stays `ƒ`.
5. `python3 scripts/skill_parity.py` → `PASS`.
6. `bash -n web/public/install.sh` → exit 0.
7. From the repo root: `python3 scripts/workflow.py validate` → passes.
8. Every §11 check above, with its evidence quoted.

If you fix anything, re-run 1–4 afterwards and report both readings.

## Out of scope

- **No redesign.** If something looks wrong but matches the contract, it is right — log it as an
  observation, do not "improve" it.
- **No `globals.css` change, no new or renamed token** — the design's delta is `None.`
- No changes to the canonical skill or `web/public/SKILL.md` beyond the temporary, restored count probe.
- Do not fix the 12 pre-existing prettier failures — they are P12's call, and `format:check` is
  deliberately not in CI.
- No backend change. No `doc-new-version` — append to `## Doc impact` in `phase.md` instead.
- No deploy, no push. `/SKILL.md` and `/install.sh` 404 until P12; nothing here is verifiable against a
  live origin.

## When done

Write `works/phases/active/P11/slices/P11.S10/result.md` from scratch (free-form): each of the seven
acceptance checks with its evidence, the padding adjudication and its reasoning, what you changed and why
(or that nothing needed changing), what remains unverifiable without a browser, and anything the phase
review should look at. Append durable cross-slice notes to `works/phases/active/P11/phase.md` — **the
review runs next**, so make sure `## Doc impact` is complete and accurate for the whole phase. Do not
commit and do not change any slice or phase status.
