# P9.S6 — Plan: Landing — reclaim `/` (the largest net-new surface)

## Context — why this slice exists

The biggest build in P9. `web/src/app/page.tsx` is a pure redirect today; `build-prompt.md §7` turns `/`
into the **public landing** for signed-out visitors while keeping the signed-in bounce to `/dashboard`.
The landing sits **outside** the `(app)` group (no app shell) and composes the primitives + brand from
S2/S3 into a marketing page. Rated **high** — most composition, the most grounded copy. Independent of
S4/S5.

Source of truth on disk (no DesignSync): `build-prompt.md §7` (§7.1 mark — already built S3; §7.2 route;
§7.3 the authored copy, **verbatim**; §7.4 the component list). Read `works/phases/active/P9/phase.md` first.

**Confirmed clean:** `NAV_LINKS`/`SKIP_TO_CONTENT` are dead leftovers (exported, never rendered); **no test
covers the `/` redirect**, so reclaiming `/` breaks nothing. Every primitive the landing needs exists.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## Files S6 owns

- Rewrite: `web/src/app/page.tsx` (redirect → landing); `web/src/content/section-ids.ts` (widen anchors).
- **New:** `web/src/content/landing.ts` (the copy); `web/src/components/landing/*` (the sections) + a barrel.

## The work

### 1. `page.tsx` — reclaim `/` (§7.2)
Server component. Keep the signed-in bounce: `const token = await getSession(); if (token) redirect("/dashboard");`
then render the landing for signed-out visitors. Rewrite the stale "P9 replaces this…" comment. It renders
its **own** nav/footer (from `components/landing/*`) — no app shell (it's outside `(app)`).

### 2. `content/section-ids.ts` — widen for the landing anchors (§4.12)
The landing's `<Section id=…>` bands need real anchors. **Widen** `SECTION_IDS` to add `features`, `how`,
`pricing` (keep `overview`/`primitives` — dead, but `nav.ts` still references them; **S7 retires them**).
Update the stale comment. (This is §4.12's deferred item; widening keeps the typed single-source-of-truth —
do not relax to `string` unless widening proves awkward.) **Do NOT touch `nav.ts`** — dead-leftover cleanup
is S7.

### 3. `content/landing.ts` — the authored copy (§7.3, verbatim)
A `LANDING` const (copy-as-data, per the app convention), transcribing **§7.3 exactly** — grounded in real
product facts, no lorem:
- **nav** (Features/How it works/Pricing/Docs; Sign in→`/login`; Start free→`/signup`)
- **hero** (eyebrow, headline "Capture the feedback your product is already getting.", the sub, CTAs
  "Start free"/"Read the docs") + the hero-visual data: a **real `POST /api/feedback` JSON body** grounded
  in the actual capture shape (`message` incl. a Korean string, `feedback_value: 2`, `source_product`, …
  — see `lib/vocky/types.ts`) beside a "captured" record (Korean message + `disliked` Badge + two `Chip` tags).
- **trust strip**, **how (3 steps)**, **showcase**, **features (6)**, **pricing** (Free "Available now" +
  muted "Pro & Teams — coming later" with the disabled "Not yet — vocky is free today" control — **copy
  only, no waitlist endpoint**, §9), **closing CTA**, **footer** (Product/Project/Account cols, "© 2026 vocky · pre-MVP").
- **Doc links** ("Read the docs", nav "Docs", footer "Documentation"/"GitHub"/"MIT license"): point at a
  **real** target (the GitHub repo `github.com/leetusik/vocky` / its README / the LICENSE) — **never a fake
  `/docs` route** that would 404. Co-locate the landing content types (or extend `content/types.ts`).

### 4. `components/landing/*` — the sections (§7.4)
Compose from the adopted primitives (do not rebuild them): `LandingNav`, `Hero`, `TrustStrip`,
`HowItWorks`, `Showcase`, `Features` (`Grid cols={3}` of `Card`/feature blocks), `Pricing`
(`Card variant="pricingFeatured"` + `pricing`), `ClosingCTA` (`Section tone="forest"`), `LandingFooter`
(`Section tone="forest"`), plus a barrel. Use `Section` tonal bands, `EndpointCard` (the forest code panel),
`Button` (`primary`/`secondary`/`dark`), `Chip`/`Badge`, `Mark`/`Wordmark` (nav uses `size={32}`; hero/empty
may use `52`; footer wordmark `tone="dark"`), and **`Reveal` sparingly** for one-shot section reveals
(via `<Section reveal>` — reduced-motion-safe already). Content width `max-w-page` (Section's inner
container already applies it). Server components throughout; `Reveal` is the only client island.

## Reuse (everything exists — do NOT rebuild)

`Section`/`Grid`/`EndpointCard`/`Reveal`/`Card` (incl. `pricing`/`pricingFeatured`/`dark`)/`Button` (incl.
`dark`)/`Chip`/`Badge` from `@/components/ui`; `Mark`/`Wordmark` from `@/components/brand`; `getSession`
from `@/lib/session`.

## Locked floors S6 must honor

- **Signed-in bounce preserved** (`/` → `/dashboard` for a live session; the landing serves signed-out only).
- `word-break: keep-all` (global — Korean in the hero/showcase examples respects it).
- **Reveal** is progressive-enhancement + reduced-motion-safe — do not add other motion.
- **No fake routes / no lorem** — every link resolves to a real target; every string is grounded (§7.3).
- **No backend** (§9) — the pricing "coming later" control is disabled copy, not a waitlist.

## Boundary — do NOT touch

App surfaces/states/components/primitives (S2–S5, done), `globals.css`/`fonts.ts` (S1). **Do NOT retire**
`nav.ts` / the dead `overview`/`primitives` ids (that's S7). No backend / `src/vocky/**` / `lib/vocky/*`
change (§9) — `lib/vocky/types.ts` is read-only reference for the hero JSON shape.

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean; **`cd web && pnpm build` green**.
- `prettier --write` the new/changed files only.
- **Behavior:** `/` serves the landing to signed-out visitors and still `redirect`s a signed-in one to
  `/dashboard` (the `getSession` bounce). No test asserts the old redirect (confirmed) — nothing to update;
  if a test does surface, update it to the landing behavior.
- Greps: `page.tsx` renders the landing (no bare `redirect(token ? …)` two-way); `content/landing.ts` +
  `components/landing/*` exist; the hero JSON contains a Korean `message`; doc links point at the real repo,
  not `/docs`.
- Smoke (recommended, high-value for the largest surface): run the dev server, load `/` signed-out → the
  full landing (nav, hero with the endpoint panel + captured card, trust strip, how, showcase, features,
  pricing, closing CTA, footer) renders in the vocky palette with Korean intact; the Start-free/Sign-in CTAs
  resolve; a signed-in session at `/` bounces to `/dashboard`.

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

The public landing now serves `/` (signed-out) with the full vocky marketing surface; `/` is no longer a
pure redirect. `frontend.md` (v0003) / `experience.md` describe `/` as a redirect and the landing as a P6
concern — now built. For `P9.REVIEW`.
