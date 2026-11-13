# P6.S3 — CSP + production security headers · result

**Status: done.** One file changed: `web/next.config.ts`. Production-gated
Content-Security-Policy added, `Permissions-Policy` tightened, four existing
headers preserved, stale P4 comment refreshed. No HSTS (edge/S6), no nonce, no
`middleware.ts` — house style preserved.

## What changed — `web/next.config.ts` (only file)

- Added `const isProd = process.env.NODE_ENV === "production"`.
- Added a `csp` array (joined with `; `) mirroring the sibling `hi2vi_web` house
  style **minus every analytics origin** — vocky's is all-`'self'`:
  ```
  default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'
  ```
- Refactored the four headers into a `baseSecurityHeaders` array that **conditionally
  appends `Content-Security-Policy` only when `isProd`**; `X-Frame-Options: DENY`
  (`frameDeny`) stays uniform on every path via `...baseSecurityHeaders, frameDeny`.
- **Upgraded `Permissions-Policy`** from `camera=(), microphone=(), geolocation=()`
  to `camera=(), microphone=(), geolocation=(), browsing-topics=()` (applies in
  dev + prod).
- Rewrote the stale lines-10-12 JSDoc: the app now ships the CSP (prod-gated); HSTS
  + the additive `upgrade-insecure-requests` CSP are the edge/nginx concern (P6.S6).
- `output: "standalone"` kept unchanged. No HSTS set here. No nonce / `middleware.ts`
  introduced.

Rationale for `'unsafe-inline'` (no nonce): required for Next App Router's nonce-less
inline hydration/bootstrap scripts, `next/font`'s injected inline `<style>`, and React
inline `style` attributes; a nonce would need a `middleware.ts` that forces dynamic
rendering and loses static generation. All other resources are same-origin (self-hosted
woff2 fonts, same-origin server-rendered OG/apple-icon PNGs + SVG favicon covered by
`img-src 'self' data:`, same-origin BFF fetch covered by `connect-src 'self'`).

## Verification (all run; actual output)

- **`pnpm build`** (in `web/`): succeeded. Next 16.2.10 compiled + TypeScript passed
  + 13/13 static pages generated. No CSP-related build error.
- **`pnpm test`** (vitest): `Test Files 5 passed (5)`, `Tests 56 passed (56)` — green.
- **CSP present in production** — `NODE_ENV=production pnpm start` then
  `curl -sI http://127.0.0.1:3030/ | grep -i content-security-policy` returned exactly:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'
  ```
  `Permissions-Policy` header confirmed to include `browsing-topics=()`. HSTS confirmed
  **not** present (correct — edge concern). Full header set on `/`: X-Content-Type-Options,
  Referrer-Policy, Permissions-Policy, Content-Security-Policy, X-Frame-Options.
- **CSP absent in dev** — `pnpm dev` then the same `curl -sI ... | grep -i
  content-security-policy` returned **no output** (confirmed). The other four headers,
  including the tightened `Permissions-Policy`, are present in dev.
- **Served page loads, no obvious CSP breakage** — `GET /` in prod returned
  `http_code=200 size=70260`, `<title>vocky</title>`. All sources `'self'`; full
  in-browser CSP-violation check is deferred to S10 smoke / REVIEW per plan.
- **`python3 scripts/workflow.py validate`** (repo root): `Workflow validation passed.`

## Deviations from plan

None. One file changed exactly as specified; CSP string matches the plan's directive
set verbatim (analytics origins dropped per the plan). S6 hand-off + Doc-impact notes
appended to `phase.md`.
