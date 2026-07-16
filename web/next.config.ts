import type { NextConfig } from "next";

/**
 * vocky web app — Next.js config (P4.S1 scaffold).
 *
 * `output: "standalone"` emits `.next/standalone/server.js` so a later deploy
 * (P6) can run the lean traced Node server in a container. It is build-only:
 * `next dev` / `next start` ignore it, so local dev is unaffected.
 *
 * Only the generic, everywhere-safe security headers ship here. A full CSP,
 * HSTS, and the production edge/nginx wiring are a P6 deploy concern (this app
 * is local-dev-only in P4). The BFF proxy + auth boundary land in P4.S2.
 */
const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default nextConfig;
