# vocky-web

The authenticated web app for vocky — a Next.js 16 / React 19 / Tailwind v4
app that surfaces the tenant dashboard, project pages, and cross-project
feedback search. It is a session-token client of vocky's `/auth/*` + `/app/*`
routes through a server-side BFF proxy; it never talks to the `vk_`-keyed
`/api/*` surface.

The palette/fonts here are **neutral placeholders** (slate surfaces + one
indigo accent, Noto Sans KR + JetBrains Mono via `next/font/google`). The real
vocky brand is finalized at the P6 design gate; the `@theme` token _names_
match hi2vi_web so P6 swaps values only.

## Auth model (the BFF)

The browser only ever talks to this Next.js origin — never to vocky directly
(vocky has no CORS). Signup/login POST to this app's own
`/api/auth/{login,signup,logout}` route handlers, which call vocky's `/auth/*`
server-to-server. The opaque 30-day bearer token vocky returns is **sealed**
(AES-256-GCM, key = `sha256(SESSION_SECRET)`) into an httpOnly, `SameSite=Strict`
cookie the app sets for itself — so the token is never readable by browser JS,
and there is no web-side database or session store.

Server guards (`src/lib/session.ts`) unseal that cookie and **return the token**,
which the server-side vocky client (`src/lib/vocky/`) injects as
`Authorization: Bearer` on `/app/*` + `/auth/*` calls. The app is a session-token
client only: it never touches the `vk_`-keyed `/api/*` surface.

## Environment

Copy `.env.example` to `.env.local` and set both server-only keys:

| Key                  | Purpose                                                                    |
| -------------------- | -------------------------------------------------------------------------- |
| `VOCKY_API_BASE_URL` | vocky API origin the server calls, e.g. `http://127.0.0.1:8000`            |
| `SESSION_SECRET`     | secret the session-sealing key is derived from (`openssl rand -base64 32`) |

Neither is `NEXT_PUBLIC_`. Rotating `SESSION_SECRET` invalidates every live
session.

## Run

```bash
corepack enable      # once, to activate the pinned pnpm
pnpm install
cp .env.example .env.local && $EDITOR .env.local
pnpm dev             # http://127.0.0.1:3030
```

`/` redirects to `/dashboard` when signed in, else `/login`.

Other scripts: `pnpm build` (standalone production build), `pnpm start`,
`pnpm lint`, `pnpm typecheck`, `pnpm test` (vitest), `pnpm format`.
