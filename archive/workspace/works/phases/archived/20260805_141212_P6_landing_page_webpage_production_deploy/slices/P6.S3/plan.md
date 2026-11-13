# P6.S3 — CSP + production security headers · plan

> Slice `P6.S3` (implementation, risk **medium**). Adds the real-origin Content-Security-Policy to the
> web app; HSTS + the additive upgrade-CSP land at the nginx edge (S6). Small surface (one file) but
> load-bearing — a wrong CSP breaks the app in production. Read `phase.md` (Findings + Constraints).

## Context

`web/next.config.ts` ships only four generic security headers and a comment deferring "a full CSP, HSTS,
and the production edge/nginx wiring" to P6. Now that the origin is known, add the CSP, mirroring the
established **sibling house style** (`hi2vi_web/next.config.ts` is the fully-formed reference;
`knowledge/web` is an unfinished scaffold like vocky's):

- **The app owns its CSP + security headers in `next.config.ts`** (prod-gated); nginx passes them
  through untouched and adds only HSTS + an additive `upgrade-insecure-requests` CSP.
- **`'unsafe-inline'` for both `script-src` and `style-src`, no nonce.** Required for Next App Router's
  nonce-less inline hydration/bootstrap scripts, `next/font`'s injected inline `<style>`, and React
  inline `style` attributes (`features.tsx`). A nonce needs `middleware.ts` that forces dynamic
  rendering and loses static generation — the house style deliberately rejects it. No `middleware.ts`
  exists in any sibling.
- **Production-only** (`isProd` gate): dev/Fast-Refresh needs `eval` + a websocket that a strict CSP breaks.

vocky's real client surface (grounded by research): fonts self-hosted (`font-src 'self'`); no
`next/image`/`<img>`/remote images (`img-src 'self' data:`); no third-party scripts/analytics/
`next/script`/`dangerouslySetInnerHTML`; BFF ⇒ browser connects same-origin only (`connect-src 'self'`);
no iframes/embeds (`frame-ancestors 'none'`, `object-src 'none'`). Every analytics origin in hi2vi's CSP
is dropped — vocky's CSP is all-`'self'`.

## Edit — `web/next.config.ts` (only file)

Add `isProd = process.env.NODE_ENV === "production"`. Keep the four existing headers on `/:path*`,
**upgrade `Permissions-Policy`** to `camera=(), microphone=(), geolocation=(), browsing-topics=()`, and
append the CSP **only when `isProd`**:

```
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'
```

Do **not** set HSTS here (edge — S6). Update the stale comment (lines 10-12): the app now ships the CSP
(prod-gated); HSTS is set by the edge vhost. Keep `output: "standalone"`.

## Hand-off to S6 (append to `phase.md` Findings/Constraints)

The nginx `vocky.conf` (S6) must, on the `:443` server, mirror the sibling house style:
`add_header Strict-Transport-Security "max-age=300" always;` (**`max-age=300`, no `includeSubDomains`,
no `preload`**) and the additive `add_header Content-Security-Policy "upgrade-insecure-requests" always;`
(composes with, does not replace, the app CSP). nginx otherwise passes the app's headers through untouched.

## Docs

Append a **Doc impact** note to `phase.md`: production CSP added in `next.config.ts` (prod-only, all
`'self'`, `'unsafe-inline'` scripts/styles for Next hydration, no nonce), Permissions-Policy tightened;
HSTS + additive upgrade-CSP deferred to the edge (S6). REVIEW folds into `docs/current/security.md` +
`frontend.md`.

## Verification

- `cd web && pnpm build` succeeds and `pnpm test` (vitest) stays green.
- **CSP is prod-only:** after build, `pnpm start` then
  `curl -sI http://127.0.0.1:3030/ | grep -i content-security-policy` shows the exact directive string;
  confirm it's **absent** under `pnpm dev`. Confirm `Permissions-Policy` includes `browsing-topics=()`.
- Sanity: served pages still load, no obvious CSP breakage (all sources `'self'`; full in-browser check
  is S10 smoke / REVIEW).
- `python3 scripts/workflow.py validate` passes (run from repo root — the shell cwd may persist; use an
  absolute path or `cd` back).

## Executor notes

One file. Mirror the referenced directive set exactly (minus analytics origins). Do not introduce a
nonce/`middleware.ts`. Do not set HSTS in Next. If the built app throws CSP violations you can't resolve
without loosening beyond the referenced set, escalate with the specific violated directive rather than
widening the policy silently. Write `result.md`; append the S6 hand-off + Doc-impact notes to `phase.md`.
Do not commit; do not transition status.
