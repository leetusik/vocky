# P9.S1 — Result: Foundations — `@theme` swap + Pretendard loader

Applied round 01's signed-off foundations into the three foundation files. **No visual component or
surface was touched** — only the tokens and the font wiring they resolve through. Every value comes
straight from `build-prompt.md §2/§3/§4`; nothing was invented or approximated.

## What changed

### `web/src/app/globals.css`
- **Colors (§2.1):** all **41 hex `--color-*` values** replaced with the vocky (deep-emerald / green-cool)
  column; token **names unchanged**; every trailing comment refreshed to the §2.1 `Role`; group header
  comments rewritten off the placeholder/hi2vi/indigo/slate language to honest vocky roles.
  - `--color-on-primary` kept **`#FFFFFF`** (§2.2 — AA 5.36:1 on the green).
  - Both intentional equalities preserved: `--color-ink == --color-canvas-dark` (`#0e1a16`) and
    `--color-archive-olive == --color-muted` (`#8a968f`). Verified in-file. No old placeholder hex
    (indigo/slate/red-600/etc.) remains anywhere.
- **shadcn alias verify (§2.5 last bullet):** confirmed — no edit needed. `--primary: var(--color-green)`,
  `--primary-foreground: var(--color-on-primary)`, `--ring: var(--color-green-deep)`,
  `--destructive: var(--color-danger)` all map **by name**, so they re-theme automatically.
- **Type scale (§3.2):** all **14 `--text-*` steps** rewritten to the exact size/lh/letter-spacing/weight.
  Weights normalized to Pretendard 400/500/600/700/800 (the odd `680`/`550`/`450` gone — grep for `680`
  now returns 0). `heading-4` **gained** `-0.2px` letter-spacing; `micro` letter-spacing set to `0.8px`
  (was `1px`). The body/caption/button/code steps carry no letter-spacing (matches the table's "—";
  they had none in the placeholder either, so nothing was removed there). Size reductions applied:
  hero-display 68→60, display-lg 56→46, heading-1 48→38, heading-2 36→30, heading-3 28→24, heading-4
  22→18, body-lg 19→18, body-md/body-md-medium 16→15, body-sm 14→13, caption 13→12; button-md lh 1.3→1.2.
- **Fonts (§3.1):** CSS var renamed `--font-noto-sans-kr` → `--font-pretendard`. `--font-sans` now leads
  `var(--font-pretendard), "Pretendard", "Noto Sans KR", -apple-system, BlinkMacSystemFont, system-ui,
  sans-serif` — **Korean-capable fallback (Noto Sans KR) retained** (locked floor). `--font-en` stops
  being a bare system stack and points at Pretendard (`var(--font-pretendard), "Pretendard", "Noto Sans
  KR", system-ui, sans-serif`), so `button.tsx`'s `font-en` call site renders in the brand face.
  `--font-mono` **unchanged** (JetBrains Mono).
- **Radius (§4.1):** base 14→**10**, md 10→**8**, lg 14→**10**, xl 18→**14**, xxl 28→**20**; xs 4 / sm 6
  unchanged. shadcn `:root { --radius }` 14→**10px**.
- **Spacing (§4.2):** only `--spacing-hero` **128→120**; section-sm/section/section-lg and both
  `--container-*` unchanged.
- **Breakpoint (§4.3):** `--breakpoint-xs: 30rem` **removed**; `--breakpoint-app: 56.25rem;` (900px)
  **added**. (The `min-[900px]:` → `app:` literal migration is **not** S1's — S1 only defines the token,
  per the distributed-migration plan; S3/S4 migrate their own files, S7 backstops.)
- **Header comment:** rewritten from the "PLACEHOLDER PALETTE … finalized at the P6 design gate" text to
  describe the applied vocky brand, grounded in `result.md §0` — deep-emerald green (always = signal) on a
  green-cool neutral ramp, light-only, compact/data-dense, Pretendard + JetBrains Mono, no gradients, the
  value-swap-names-kept re-theme property, applied by P9 from round 01 signoff. The "No `.dark` block on
  purpose" note kept (still true). Nothing invented.

### `web/src/lib/fonts.ts`
- Replaced the `Noto_Sans_KR` (`next/font/google`) import with a **`next/font/local`** load of a vendored
  Pretendard variable woff2. Export renamed `notoSansKr` → `pretendard`, exposing `variable:
  "--font-pretendard"`, `weight: "400 800"` (variable range covering the 400–800 the type scale uses),
  `display: "swap"`, and a `fallback: ["Pretendard", "Noto Sans KR", "system-ui", "sans-serif"]`. The
  file's doc comment rewritten off the "placeholder … P6 design gate" language. **JetBrains Mono kept on
  `next/font/google` unchanged.**

### `web/src/app/layout.tsx`
- Renamed the import/usage `notoSansKr` → `pretendard`; `<html className>` now wires
  `${pretendard.variable} ${jetbrainsMono.variable}`; the stale "Noto Sans KR font" comment updated to
  "Pretendard (Noto Sans KR fallback)". No other change.

## Pretendard mechanism + where the asset lives

- **Mechanism:** `next/font/local` + a single vendored **variable** woff2 (recommended path in the plan).
  Self-contained, no runtime dependency, one file covers all weights, and matches the app's existing
  self-host philosophy (it already self-hosts JetBrains Mono via `next/font`).
- **Asset:** `web/src/lib/fonts/PretendardVariable.woff2` — **co-located** for `fonts.ts`
  (`src: "./fonts/PretendardVariable.woff2"`). 2,057,688 bytes, genuine woff2 (magic `wOF2`, TrueType
  variable, Pretendard v1.2.x). Fetched from the official source: Pretendard GitHub
  (`orioncactus/pretendard`, `packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2`).
  Not gitignored (verified with `git check-ignore`). The primary face is genuinely Pretendard — the
  `pnpm build` success below proves `next/font/local` resolved and processed the asset (not a fallback).

## Verification (all clean)

| Command | Result |
|---|---|
| `pnpm typecheck` (`tsc --noEmit`) | **pass** — no output |
| `pnpm lint` (`eslint .`) | **pass** — no output |
| `pnpm build` (`next build`) | **pass** — "✓ Compiled successfully in 1657ms", TypeScript finished, 7/7 static pages generated, all 12 routes emitted. Proves the `next/font/local` Pretendard loader resolves the vendored woff2 and compiles. |
| `prettier --write` (3 touched files only) | all three already **unchanged** (clean) |

Grep assertions (against `src/app/globals.css`):
- `--breakpoint-xs` → **gone**; `--breakpoint-app: 56.25rem;` → **present** (line 184).
- `--font-sans` → leads with `var(--font-pretendard)`, retains `"Noto Sans KR"` Korean fallback.
- `--font-en` → points at Pretendard (no longer a bare system stack).
- `--font-mono` → **unchanged** (`var(--font-jetbrains-mono), "SF Mono", Menlo, Consolas, monospace`).
- Old placeholder hexes (indigo/slate/red-600/amber-600 set) → **none remain**.
- Hex-valued `--color-*` tokens = **41**; `--text-*` size steps = **14**; `680` occurrences = **0**.

Note on `format:check`: repo has 20 pre-existing unrelated `format:check` failures — I ran
`prettier --write` on **only** my three touched files (all already clean), touching none of the others.

## Notes for downstream slices

- **Font var name is `--font-pretendard`** (the CSS var and the `next/font/local` `variable`). Any later
  reference to the old `--font-noto-sans-kr` / `notoSansKr` symbol would be stale — the rename surface was
  exactly these three files (confirmed: nothing else imported `notoSansKr`, and the build is green).
- **S2 owns the §2.5 hardcoded-literal fixes** (`button.tsx` two `primary` shadows `rgba(79,70,229,…)` →
  green `rgba(12,122,82,…)`; `card.tsx` `feature`/`pricing` ink shadows, `pricingFeatured` border/shadow,
  `archive` `#e2e8f0` → `border-hairline`). S1 deliberately did **not** touch those — they'd be thrown
  away by S2's wholesale rewrite. The shadcn *alias* verify (§2.5 last bullet) is done.
- **`--breakpoint-app` is defined but not yet consumed.** The 11 `min-[900px]:` literals still live in
  `app-shell.tsx`/`rail-nav.tsx`/`feedback/*`; S3 migrates app-shell/rail-nav, S4 the feedback pages, S7
  backstops (zero `min-[900px]:` / `--breakpoint-xs`). No `app:` variant is consumed anywhere yet, which
  is expected.
- **`--font-en` now resolves to Pretendard**, so `button.tsx:18`'s `font-en` will render brand type once
  S2 rewrites the button — no extra wiring needed there.
- The vendored woff2 (~2 MB) is a committed binary the orchestrator will pick up under
  `web/src/lib/fonts/`.

## Deviations from `plan.md`

None. The plan's recommended mechanism (`next/font/local` + vendored variable woff2) was viable — the
official Pretendard woff2 was obtainable — so the fetch-failure `needs_operator` protocol did not trigger.
Weight range expressed as `"400 800"` (the plan offered `"45 920"` or `"400 800"`); `400 800` matches the
type scale's actual weight span exactly.
