import type { NextConfig } from "next";

/**
 * vocky web app — Next.js config (P4.S1 scaffold; CSP added P6.S3).
 *
 * `output: "standalone"` emits `.next/standalone/server.js` so the P6 deploy can
 * run the lean traced Node server in a container. It is build-only: `next dev` /
 * `next start` ignore it, so local dev is unaffected.
 *
 * The app owns its CSP + security headers here (production-gated). HSTS and the
 * additive `upgrade-insecure-requests` CSP are set by the edge/nginx vhost (P6.S6)
 * after TLS at the edge — not in this app. The BFF proxy + auth boundary land in
 * P4.S2.
 */
const isProd = process.env.NODE_ENV === "production";

// Content-Security-Policy (P6.S3) — pragmatic, static-rendering-preserving.
// 'unsafe-inline' (script/style) covers Next App Router's nonce-less inline
// hydration/bootstrap scripts, next/font's injected inline <style>, and React
// inline `style` attributes; every other resource is same-origin (self-hosted
// woff2 fonts, same-origin server-rendered PNGs / SVG favicon, the same-origin
// BFF fetch). No nonce: a per-request nonce needs a middleware that would force
// dynamic rendering and lose static generation — the house style deliberately
// rejects it (no middleware.ts exists). Applied in PRODUCTION ONLY — dev (Fast
// Refresh) needs eval + a websocket a strict CSP would break. HSTS +
// upgrade-insecure-requests are deferred to the edge vhost (P6.S6). This CSP
// string is mirrored into docs/current/security.md at P6.REVIEW.
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "object-src 'none'",
].join("; ");

// Security headers that apply EVERYWHERE.
const baseSecurityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  },
  ...(isProd ? [{ key: "Content-Security-Policy", value: csp }] : []),
];

const frameDeny = { key: "X-Frame-Options", value: "DENY" };

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    // X-Frame-Options: DENY uniformly on every path (the prod CSP also carries
    // frame-ancestors 'none').
    return [
      { source: "/:path*", headers: [...baseSecurityHeaders, frameDeny] },
    ];
  },
};

export default nextConfig;
