# vocky-web

The authenticated web app for vocky — a Next.js 16 / React 19 / Tailwind v4
app that surfaces the tenant dashboard, project pages, and cross-project
feedback search. It is a session-token client of vocky's `/auth/*` + `/app/*`
routes through a server-side BFF proxy (added in P4.S2); it never talks to the
`vk_`-keyed `/api/*` surface.

This slice (P4.S1) is the design-system foundation only: the Tailwind-v4
`@theme` token system, the CVA primitive set (`+ data-table`), the
copy-as-data `src/content/` convention, and a `/` design-system preview page.
It is purely presentational — no vocky API calls, no auth, no business pages.

The palette/fonts here are **neutral placeholders** (slate surfaces + one
indigo accent, Noto Sans KR + JetBrains Mono via `next/font/google`). The real
vocky brand is finalized at the P6 design gate; the `@theme` token *names*
match hi2vi_web so P6 swaps values only.

## Run

```bash
corepack enable      # once, to activate the pinned pnpm
pnpm install
pnpm dev             # http://127.0.0.1:3030
```

Other scripts: `pnpm build` (standalone production build), `pnpm start`,
`pnpm lint`, `pnpm typecheck`, `pnpm format`.
