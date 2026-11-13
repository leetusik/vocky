# P4.S1 — Plan: App scaffold + design-system foundation

Orchestrator's native plan for slice **P4.S1** (`implementation`, `medium` → executed by **`slice-executor-mid`**). Foundation slice: it stands up the Next.js app in `web/` and ports the hi2vi_web design system. **Purely presentational — no vocky API calls, no auth, no business pages, no production deploy config.** Those are S2+.

## Context

P4 builds vocky's authenticated web app as a new Next.js app in a repo subdirectory `web/` (decision D-P4-1), modeled on `~/projects/personal/hi2vi_web`. S1 is the load-bearing foundation every later page builds on: the app scaffold + the ported Tailwind-v4 `@theme` design system + CVA primitives + a **new data-table primitive** + the `design/canvas/` mirror. It produces a `pnpm dev`-runnable app whose placeholder page renders the primitives/tokens, proving the foundation before S2 wires auth/data.

Reference app fully mapped: stack is **Next.js 16 (App Router, `output:'standalone'`) · React 19 · Tailwind v4 CSS-first (no `tailwind.config.*`) · hand-rolled CVA primitives · pnpm · TS 6**.

## Placeholder decisions (operator-approved; "finalize at P6" per phase open questions)

- **Palette:** port the hi2vi_web `@theme` token *structure/group-shape* but with a **neutral placeholder palette** — a slate/zinc surface ramp + one accent (e.g. indigo/blue) + standard danger/caution signal states — **not** hi2vi's green brand. Same token *names* as hi2vi so P6 swaps values only. Token names unchanged ⇒ `cn()`'s type-scale list stays identical.
- **Fonts:** use **`next/font/google`** (build-time self-hosted, CSP-safe, no vendored binaries, no subset toolchain): **`Noto_Sans_KR`** → `--font-sans` (Korean-capable — the app renders Korean feedback) + **`JetBrains_Mono`** → `--font-mono`, wired via CSS-var → `@theme` font-family exactly like hi2vi. Swappable to Pretendard/vocky brand at P6. (Do **not** copy hi2vi's 8 self-hosted faces or the Korean-clip micro-subsets.)
- **Chrome language:** root `lang="en"` with all copy centralized in `src/content/` (one-line localization later). Korean *content* renders fine via Noto Sans KR regardless.

## What S1 builds (all under `web/`)

**1. Project scaffold**
- `web/package.json` — `name: vocky-web`, `private`, `packageManager: pnpm@10.28.2`, `engines.node >=22.13.0`; scripts `dev`/`build`/`start`/`lint`/`format`/`format:check`/`typecheck` (mirror hi2vi's, bind `127.0.0.1 -p 3030`). **Scaffold-only deps** (match hi2vi ranges): `next@^16.2.9 react@^19.2.7 react-dom@^19.2.7 class-variance-authority@^0.7.1 clsx@^2.1.1 tailwind-merge@^3.6.0 tw-animate-css@^1.4.0 lucide-react@^1.21.0`; **devDeps** `typescript@^6.0.3 @types/node@^22.20.0 @types/react@^19.2.17 @types/react-dom@^19.2.3 tailwindcss@^4.3.1 @tailwindcss/postcss@^4.3.1 eslint@^9.39.4 eslint-config-next@^16.2.9 prettier@^3.8.4 prettier-plugin-tailwindcss@^0.8.0`. **Drop all hi2vi feature deps** (`@google/genai openai nodemailer marked sanitize-html sharp server-only` + their `@types`; `zod` deferred to S2's forms).
- `web/.nvmrc` → `22`. `web/.gitignore` → `node_modules/ .next/ out/ .env*.local next-env.d.ts`. `web/README.md` — one-paragraph "how to run" (`pnpm install && pnpm dev`).
- Config files (contents per the reference, feature bits stripped):
  - `web/tsconfig.json` — Next 16 defaults + `"paths": { "@/*": ["./src/*"] }`.
  - `web/postcss.config.mjs` — `{ plugins: { "@tailwindcss/postcss": {} } }`.
  - `web/eslint.config.mjs` — `import next from "eslint-config-next"; export default [...next]`.
  - `web/.prettierrc` — `{ "plugins": ["prettier-plugin-tailwindcss"], "tailwindStylesheet": "./src/app/globals.css" }` (+ `.prettierignore`).
  - `web/components.json` — shadcn `new-york`, `tailwind.config: ""` (CSS-first), `css: src/app/globals.css`, the `@/*` aliases.
  - `web/next.config.ts` — `output: "standalone"` + the generic security headers (`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `X-Frame-Options: DENY`). **Drop** `outputFileTracingIncludes`, the analytics-CSP, and hard-coded dev IPs (a full CSP is a P6 deploy concern).
  - **No `tailwind.config.*`** (Tailwind v4 is 100% CSS-first via `globals.css`).

**2. Design-system foundation** (`web/src/app/globals.css` + `web/src/lib/` + `web/src/components/ui/`)
- `web/src/app/globals.css` — keep hi2vi's **4-part skeleton**: `@import "tailwindcss"` + `@import "tw-animate-css"` → `@theme { … }` token groups (colors, font families, type scale *with* bundled `--…--line-height/--letter-spacing/--font-weight` sub-props, radius, named spacing, container widths, `--breakpoint-xs`) → `:root { shadcn semantic aliases }` + `@theme inline { bridge to --color-* utilities }` (incl. `--destructive`) → `@layer base { body bg/font/text, :focus-visible ring, prefers-reduced-motion block, h1–h6 word-break:keep-all }`. Use the **neutral placeholder palette**. **No `.dark` block** (explicit surface tokens; keep hi2vi's "no dark-mode toggle" note). **Drop** hi2vi's ~1600 lines of hero/flywheel/pkg/modal component CSS.
- `web/src/lib/utils.ts` — port `cn()` **verbatim**, including the `extendTailwindMerge({ extend: { classGroups: { "font-size": [{ text: [...] }] } } })` registering the custom `text-*` type-scale names (same names as the `@theme` scale, so the list is copied as-is). This keeps `cn("text-heading-2","text-fg")` from dropping the size.
- `web/src/components/ui/` — port the CVA primitive set, retoned to the placeholder palette: `button.tsx`, `card.tsx`, `badge.tsx`, `field.tsx` (Label/Input/Textarea/Checkbox/FieldError), `grid.tsx` (static `cols` map), `section.tsx`, `endpoint-card.tsx`, `reveal.tsx` (`"use client"` IntersectionObserver, reduced-motion-safe), and the `index.ts` barrel (re-export each component + its `*Variants` + `*Props`).
- **NEW `web/src/components/ui/data-table.tsx`** — the primitive hi2vi lacks; the dashboard's projects/credentials/feedback lists need it. A headless, token-styled table: typed `columns` (header + cell render) + `rows`, sensible defaults (hairline borders, `text-caption` headers, hover row, `overflow-x-auto` wrapper so it never breaks the page), an empty-state slot, and an optional right-aligned actions column. Add it to the barrel. Keep it presentational (data passed as props — no fetching).

**3. Copy-as-data + app skeleton**
- `web/src/content/` — the barrel convention: `types.ts`, `site.ts` (`SITE`: name/url/title/description), `nav.ts` (placeholder nav items), `section-ids.ts` (`SectionId` union), `index.ts` (re-export consts + types). Defer feature copy.
- `web/src/lib/fonts.ts` — `next/font/google` `Noto_Sans_KR` + `JetBrains_Mono`, each exposing its CSS variable for the `@theme` font families.
- `web/src/app/layout.tsx` — root layout: `lang="en"`, apply the two font `.variable` classes to `<html>`, `<body className="… bg-canvas font-sans text-fg">`, `import "./globals.css"`, minimal `metadata` (title/description from `SITE`). Icon/OG/robots/sitemap file-convention routes are **P6**, not S1.
- `web/src/app/page.tsx` — a minimal **design-system preview** page (renders a few buttons/badges/cards/a `Grid` + a sample `DataTable` with static rows). Doubles as the S1 smoke test that the tokens + primitives render. The auth-gated `(app)` route group is **S2's** job — document it as the next step, don't build it.

**4. design/canvas scaffold** (`web/design/canvas/`) — replicate the shape even though the heavy session is P6:
- `tokens.css` — a 1:1 `:root` mirror of `globals.css`'s `@theme` values (single source every card `<link>`s). For canvas font rendering, use system/fallback or a plain web-font `<link>` (canvas is a standalone design artifact, not under the app CSP) — do **not** vendor woff2.
- `_ds_manifest.json` — `namespace` (`VockyDesignSystem_<short>`), `tokens[]` (mirrored from tokens.css), `fonts[]`, and a small `cards[]` list.
- `foundations/{colors,type,spacing-radius}.html`, `components/{button,card,badge,field,grid,section}.html` — token/primitive specimen cards, each with the `<!-- @dsCard group="…" name="…" -->` first-line marker. `sections/` may hold a single placeholder card. `README.md` — the mechanism + a canvas↔repo mapping table stub.

## Key adaptations vs. straight copy
- Retone every token/primitive from hi2vi's green brand to the neutral placeholder palette; **keep token names** so `cn()`'s scale list and P6's swap stay clean.
- Add the net-new `data-table` primitive.
- Strip all feature code/deps/CSS and Korean-clip/Pretendard font machinery.

## Verification (S1 writes no vocky-calling code)
1. `cd web && corepack enable && pnpm install` succeeds (enable pnpm via corepack if absent; it's pinned by `packageManager`).
2. `pnpm typecheck` (`tsc --noEmit`) — clean.
3. `pnpm lint` (`eslint .`) — clean.
4. `pnpm build` — succeeds (Next standalone build).
5. `pnpm dev` — the `/` preview page renders the primitives + tokens (manual smoke; screenshot/curl optional).
6. `grep -rn "fetch\|/auth\|/app/\|vocky" web/src` — confirms **no** backend calls (foundation only).
7. `python3 scripts/workflow.py validate` — state integrity passes.
- **Network fallback:** if the sandbox blocks `pnpm install`/`build`, still write every file, capture the exact failing command + error, and return **`needs_operator`** (operator runs `cd web && pnpm install && pnpm typecheck && pnpm build` locally) rather than claiming a green build. Do not fabricate build success.

## Executor guardrails
- Everything lands under `web/`; touch **no** `src/vocky/**` (the Python backend) and **no** `works/**` except this slice's `result.md` + the `phase.md` note.
- No vocky API client, no auth, no `(app)` routes, no Dockerfile/compose/nginx (all S2/P6).
- Write `web/…` files + `works/phases/active/P4/slices/P4.S1/result.md`; append a one-line "Landed changes" note under `phase.md`'s Doc-impact list. **No** commits, **no** `doc-new-version`, **no** status transitions (orchestrator's job). Return a structured verdict.
