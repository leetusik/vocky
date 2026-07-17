# P9.S6 — Result: Landing — reclaimed `/`

**Status: done.** `/` is now the public vocky landing for signed-out visitors, with
the signed-in bounce to `/dashboard` preserved. Built faithfully from
`build-prompt.md §7` — every designed section, grounded copy, real doc links, no
lorem, no fake routes, no backend change.

## What shipped

### Route — `web/src/app/page.tsx` (rewrite)
Server component. `const token = await getSession(); if (token) redirect("/dashboard");`
then renders the landing (`<LandingNav/>` · `<main id="main-content">` with the seven
sections · `<LandingFooter/>`). Outside the `(app)` group → no app shell; it renders
its own nav + footer. The stale "P9 replaces this…" comment is gone.

### Anchors — `web/src/content/section-ids.ts` (widen, not relax)
`SECTION_IDS` widened to add `features` / `how` / `pricing` (the landing's real
`<Section id>` anchors, referenced by the nav via `#${SECTION_IDS.*}` so they never
drift). Kept `overview` / `primitives` (dead — still referenced by `nav.ts`; S7
retires both together). Type stayed the typed union, not relaxed to `string`.

### Copy — `web/src/content/landing.ts` (new) + `content/index.ts` barrel line
A single `LANDING` const (copy-as-data, `as const`, the S1/states convention),
transcribing §7.3 verbatim: nav, hero, trust strip, how (3 steps), showcase,
features (6), pricing (Free + muted Pro), closing CTA, footer. Also added one barrel
line to `content/index.ts` (`export { LANDING } from "./landing"`) — the same
additive pattern S5 used for `STATES`, so consumers import from `@/content`. Landing
content types are co-located in `landing.ts` (types.ts not touched — not S6-owned).

**Doc-link targets (all real, all resolve — verified: repo `github.com/leetusik/vocky`,
branch `main`, root MIT `LICENSE` + `README.md`):**
- nav "Docs", hero/closing "Read the docs", footer "Documentation" → `https://github.com/leetusik/vocky#readme`
- footer "GitHub" → `https://github.com/leetusik/vocky`
- footer "MIT license" → `https://github.com/leetusik/vocky/blob/main/LICENSE`
- trust strip "MIT-licensed" is a plain fact label (not a link)

No `/docs` (or any fake) route anywhere — grep-confirmed.

**The hero request JSON (authored, grounded in `lib/vocky/types.ts` capture shape):**
```json
{
  "source_product": "checkout-web",
  "message": "결제 단계에서 카드가 자꾸 거절돼요.",
  "feedback_value": 2,
  "target_type": "message",
  "tags": ["결제", "checkout"]
}
```
`feedback_value: 2` = dislike (mirrors the captured card's `disliked` Badge);
`target_type: "message"` is a real enum value; the two `tags` are what the trust
strip's "search 결제 or checkout" finds; the Korean `message` reappears verbatim in
the captured record card and (with English rows) in the showcase table.

### Sections — `web/src/components/landing/*` (new, 9 + barrel)
All server components; the only client island is `<Reveal>` inside `<Section reveal>`
(reduced-motion-safe). Composed from the **existing** primitives — none rebuilt:
- **`landing-nav.tsx`** — sticky translucent `<header>`; Mark 32 + Wordmark · anchor
  links (collapse < md, duplicated in footer) · Sign in (ghost) + Start free (primary)
  CTAs.
- **`hero.tsx`** — no Reveal (above the fold). Two-column: eyebrow pill / headline
  (`text-heading-1 → display-lg → hero-display`) / sub / CTAs, beside the proof — an
  `EndpointCard` (`POST /api/feedback` label + auth header + the JSON body) layered
  over a captured-record `Card` (meta · `disliked` Badge · Korean message with
  `break-keep` · two `Chip` tags).
- **`trust-strip.tsx`** — thin `surfaceSoft` band (padding trimmed via className), 4
  dot-separated facts, first in mono; `break-keep` on the Korean.
- **`how-it-works.tsx`** — `Section id="how" reveal`; `Grid cols={3}` of step cards,
  each with a numbered green-soft token.
- **`showcase.tsx`** — `reveal`; a browser-framed mock (decorative window chrome +
  non-link address pill) around a compact When/Project/Feedback/Rating table styled to
  match the app's DataTable, rows carrying rating `Badge`s (liked/disliked/unrated),
  Korean + English, `break-keep` on message cells.
- **`features.tsx`** — `Section id="features" reveal`; `Grid cols={3}` of 6 feature
  Cards, each with a small three-bar green waveform accent (the brand motif) + title +
  grounded sentence.
- **`pricing.tsx`** — `Section id="pricing" reveal`; `Card variant="pricingFeatured"`
  Free (accent Badge "Available now", $0, inclusions, Start-free CTA) beside
  `variant="pricing"` muted Pro ("—", items, **disabled** `Button` "Not yet — vocky is
  free today" — copy only, no waitlist, §9).
- **`closing-cta.tsx`** — `Section tone="forest" reveal`; heading + sub + primary
  Start-free / `dark` Read-the-docs CTAs.
- **`landing-footer.tsx`** — `<footer>` wrapping `Section tone="forest"`; brand lockup
  (Mark + `Wordmark tone="dark"`) + tagline, three link columns (Product / Project /
  Account, externals `target="_blank" rel="noopener noreferrer"`), legal line.

## Verification

| Command | Result |
|---|---|
| `pnpm typecheck` | **clean** (`tsc --noEmit`, no output) |
| `pnpm lint` | **clean** (`eslint .`, no output) |
| `pnpm build` | **GREEN** — compiled in ~1.6s, all routes build; `/` is `ƒ` (dynamic, server-rendered — correct, reads the session cookie) |
| `prettier --write` (new/changed only) | reformatted 6 files; `prettier --check` on all S6 files → "All matched files use Prettier code style!" (the 20 pre-existing unrelated `format:check` failures left untouched) |

**Dev-server smoke (`next dev`, 127.0.0.1:3030):**
- Signed-out `GET /` → **200**; HTML carries all sections — 24/24 grep-asserts pass
  (nav wordmark, hero headline + eyebrow, `POST /api/feedback` label, hero JSON Korean
  message, `Disliked` badge, `결제`/`checkout` chips, trust facts incl. "search 결제 or
  checkout", how heading + steps, showcase heading + Korean row `배송 조회가 안 돼요.`,
  features heading + items, pricing heading + "Available now" + "Not yet — vocky is
  free today", closing heading, footer legal `© 2026 vocky · pre-MVP`, footer "MIT
  license", `github.com/leetusik/vocky`). Fake-route guard: **no** `/docs` link.
- Signed-in `GET /` (forged valid `vocky_session` cookie via the app's own
  AES-256-GCM seal) → **307 → `/dashboard`** (bounce preserved).
- Tampered cookie → **200** landing (treated as signed-out, no crash).

**Boundary guard (git status):** only `page.tsx`, `content/section-ids.ts`,
`content/index.ts` (one barrel line), new `content/landing.ts`, new
`components/landing/` were changed. **No** touch to `nav.ts`, `globals.css`,
`fonts.ts`, `components/ui/*`, `components/app-shell/*`, `components/usage/*`,
`components/brand/*`, or any app/auth surface. No `min-[900px]:` introduced. No
`src/vocky/**` / `lib/vocky/*` change.

## Locked floors held
- Signed-in bounce preserved (`getSession()` → `/dashboard`); landing serves signed-out only.
- `break-keep` (word-break: keep-all) on every Korean body example (hero captured
  message, showcase message cells, trust strip) — the global heading rule made
  explicit for body copy.
- Reveal is the only motion, and only on the below-the-fold bands (how / showcase /
  features / pricing / closing) — reduced-motion-safe by the island's own contract;
  hero and trust strip stay static (above/at the fold).
- No fake routes, no lorem — every link resolves, every string grounded in real
  product facts.
- No backend — pricing "coming later" is a disabled control, not a waitlist.

## Deviations from plan
- **One additive line to `content/index.ts`** (`export { LANDING } from "./landing"`).
  Not in the plan's explicit owned-file list, but it is the established barrel
  convention (S5 did the identical thing for `STATES`) so consumers import
  `LANDING` from `@/content`. Additive, conflicts with no other slice. Everything
  else exactly per plan.

## Notes for S7 (the sweep)
- **`content/nav.ts` and the dead `overview`/`primitives` ids are now unambiguously
  dead and ready to retire.** The landing does NOT use `NAV_LINKS` or `SKIP_TO_CONTENT`
  (it builds its own nav from `LANDING.nav`, and its skip target is `#main-content`
  set directly on `page.tsx`'s `<main>`). The ONLY remaining reference to `overview`/
  `primitives` is `nav.ts` itself (which nothing renders). S7 can delete `nav.ts`,
  drop its barrel exports from `content/index.ts` (`NAV_LINKS`, `SKIP_TO_CONTENT`), and
  remove `overview`/`primitives` from `SECTION_IDS` in one move — nothing else touches
  them. (`SECTION_IDS.features`/`how`/`pricing` stay — the landing anchors.)
- The landing-nav mid links collapse below `md` (a deliberate responsive choice, not a
  dropped element — they are duplicated in the footer's Product column). If the
  operator wants a mobile menu, that is net-new client JS (a disclosure island), not in
  this round's design.
- Feature-card accent is a small three-bar green waveform (the brand motif), authored
  because the deleted Landing artifact's per-feature iconography wasn't on disk; it's
  the closest-to-intent brand-consistent choice, not a plainer fallback. Operator can
  eyeball at commit / S7.
