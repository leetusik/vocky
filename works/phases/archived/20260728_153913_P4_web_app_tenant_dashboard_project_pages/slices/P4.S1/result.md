# P4.S1 — Result: App scaffold + design-system foundation

Stood up the vocky web app in `web/` (Next.js 16 / React 19 / TS 6 / Tailwind v4
CSS-first, pnpm), templated on hi2vi_web and ported to a **neutral placeholder
palette**. Purely presentational — no vocky API calls, no auth, no business
pages, no deploy config. A `pnpm dev`-runnable `/` design-system preview renders
every ported primitive + the new `data-table`.

## What was scaffolded (all under `web/`)

**Project scaffold**
- `package.json` (`vocky-web`, `packageManager: pnpm@10.28.2`, node `>=22.13.0`;
  scripts bind `127.0.0.1 -p 3030`), scaffold-only deps (all hi2vi feature deps
  dropped: `@google/genai openai nodemailer marked sanitize-html sharp
  server-only zod` + their `@types`).
- `.nvmrc` (`22`), `.gitignore`, `README.md`, `tsconfig.json` (`@/*` → `./src/*`),
  `postcss.config.mjs`, `eslint.config.mjs` (`[...next]`), `.prettierrc` +
  `.prettierignore`, `components.json` (new-york, CSS-first), `next.config.ts`
  (`output: "standalone"` + generic security headers only — CSP/analytics/dev-IPs
  dropped as a P6 concern). No `tailwind.config.*`.

**Design system**
- `src/app/globals.css` — hi2vi's 4-part skeleton (`@theme` tokens → `:root`
  shadcn aliases → `@theme inline` bridge → `@layer base`), retoned to the
  placeholder palette. Dropped the ~1600 lines of hero/flywheel/pkg/modal CSS
  and all hero-clip keyframes; kept the `[data-reveal]`/`.is-visible` scroll-reveal
  rules that `reveal.tsx` depends on, plus focus ring, reduced-motion block, and
  `h1–h6 { word-break: keep-all }`. No `.dark` block.
- `src/lib/utils.ts` — `cn()` ported verbatim (including the `extendTailwindMerge`
  `font-size` group registering the custom `text-*` scale — same names as hi2vi).
- `src/lib/fonts.ts` — `next/font/google` `Noto_Sans_KR` (→ `--font-sans`) +
  `JetBrains_Mono` (→ `--font-mono`), each `variable`-wired for the `@theme`
  font families. `latin` subset + explicit weights `400/500/700`.
- `src/components/ui/` — CVA primitives retoned: `button`, `card`, `badge`,
  `field` (Label/Input/Textarea/Checkbox/FieldError), `grid`, `section`,
  `endpoint-card`, `reveal`, and the `index.ts` barrel.
- **NEW `src/components/ui/data-table.tsx`** — headless, generically-typed
  (`DataTable<T>`) token-styled table: `columns` (header + `cell` renderer,
  optional `align`/`actions`), `rows` + `rowKey`, `overflow-x-auto` wrapper,
  `text-caption` headers, hover rows, and an empty-state slot (`empty`). Added to
  the barrel. Presentational — data is passed as props, never fetched.

**Copy-as-data + app skeleton**
- `src/content/` — `types.ts`, `site.ts` (`SITE`), `nav.ts` (placeholder nav +
  skip link), `section-ids.ts` (`SectionId` union), `index.ts` barrel. Chrome
  copy is English; feature copy deferred.
- `src/app/layout.tsx` — root layout `lang="en"`, both font `.variable` classes
  on `<html>`, `<body class="… bg-canvas font-sans text-ink antialiased">`,
  `import "./globals.css"`, minimal `metadata` from `SITE`.
- `src/app/page.tsx` — design-system preview (buttons / badges / cards in a Grid /
  a populated + an empty `DataTable`). S1 smoke test; documents that the auth-gated
  `(app)` route group is S2's job.

**design/canvas scaffold** (`web/design/canvas/`)
- `tokens.css` — 1:1 `:root` mirror of the `@theme` values; fonts via a Google
  Fonts `@import` (standalone artifact, no vendored woff2).
- `_ds_manifest.json` — `namespace VockyDesignSystem_<short>`, 125 mirrored
  `tokens[]`, `fonts[]`, 10 `cards[]` (generated from `tokens.css` so it stays in
  sync).
- `foundations/{colors,type,spacing-radius}.html`,
  `components/{button,card,badge,field,grid,section}.html`,
  `sections/dashboard-placeholder.html` — each with the `<!-- @dsCard … -->`
  first-line marker. `README.md` — mechanism + canvas↔repo mapping table.

## Placeholder palette / font choices

- **Palette:** hi2vi's green brand → a **slate surface ramp + one indigo accent +
  standard red/amber signals**, keeping every hi2vi token *name*:
  - accent (`green*` group): `green #6366f1` (indigo-500), `green-deep #4f46e5`,
    `green-dark #4338ca`, `green-soft #e0e7ff`.
  - dark surfaces/text (`ink/forest*/charcoal/slate/steel/muted`): slate-900→400.
  - signals: `danger #dc2626` (red-600) + `caution #d97706` (amber-600) with their
    surface/hairline tints.
  - **`on-primary` flipped `#061512` → `#ffffff`**: hi2vi's bright-green CTA took
    dark text; the indigo accent is dark, so text on it must be white for contrast.
  - Retoned the hardcoded rgba shadows/borders in `button.tsx`/`card.tsx` from
    green/ink to indigo/slate; `badge` archive one-off text → `text-slate`; card
    archive one-off border `#E5E1B8` → `#e2e8f0`.
- **Fonts:** `Noto_Sans_KR` (Korean-capable, for Korean feedback content) as
  `--font-sans`, `JetBrains_Mono` as `--font-mono`, both build-time self-hosted
  via `next/font/google` (no vendored binaries, no subset toolchain). Kept the
  `--font-en` token *name* (Button uses `font-en`) but pointed it at a plain
  system stack — no vendored English face in S1. Did **not** copy hi2vi's 8
  self-hosted faces or Korean-clip micro-subsets.

## Verification (each command + outcome)

Run from `web/` unless noted:

| Command | Outcome |
| --- | --- |
| `corepack enable` | ok (pnpm 10.28.2 active) |
| `pnpm install` | **pass** — 360 packages, done in ~6s (sharp/unrs-resolver build scripts ignored, expected) |
| `pnpm typecheck` (`tsc --noEmit`) | **pass** — clean, no errors |
| `pnpm lint` (`eslint .`) | **pass** — clean, no errors/warnings |
| `pnpm build` (`next build`) | **pass** — compiled, TS ok, `/` + `/_not-found` prerendered static, `.next/standalone/server.js` emitted; Google fonts fetched fine |
| `grep -rn "fetch(\|/auth/\|/app/" web/src` | **pass** — no matches (no backend calls); bare `vocky` matches are brand/comment only |
| `python3 scripts/workflow.py validate` (repo root) | **pass** — "Workflow validation passed." |

`pnpm dev` (manual `/` smoke) not scripted here, but the identical static
prerender of `/` in `pnpm build` exercises the same render path.

Git tracking: `web/pnpm-lock.yaml` + all source are untracked-and-trackable;
`web/node_modules`, `web/.next`, `web/next-env.d.ts` are correctly gitignored.

## Deviations from plan.md

- **`text-fg` → `text-ink`.** The plan wrote `<body className="… text-fg">`, but
  no `fg` token exists in the ported (name-preserving) set; hi2vi's real
  foreground token is `ink`. Used `text-ink` (and `text-ink`/`text-slate`/
  `text-steel` on the preview page) to honor "keep the same token names as
  hi2vi". Body color is also set by the `@layer base` `body` rule regardless.
- Otherwise none. `endpoint-card.tsx` + `reveal.tsx` were ported verbatim (the
  plan's primitive list names them); their tokens auto-retone via `globals.css`.
