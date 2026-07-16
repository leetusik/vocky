import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const resolvePath = (relative: string) =>
  fileURLToPath(new URL(relative, import.meta.url));

/**
 * Vitest config (P4.S2) — deliberately minimal; the only two entries that carry
 * weight are the aliases:
 *
 *   `@`           — mirrors tsconfig's `@/*` → `./src` path mapping.
 *   `server-only` — the real package THROWS on import outside a React Server
 *                   Component graph (that is its entire job). The modules under
 *                   test are server-only by design, so tests alias it to an inert
 *                   stub. This only affects the test run: `next build` still
 *                   resolves the real package, so the guarantee that no client
 *                   bundle can import the session key remains enforced.
 *
 * Tests are Node-environment (no jsdom): everything under test is server-side
 * crypto, route handlers, and guards.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": resolvePath("./src"),
      "server-only": resolvePath("./tests/stubs/server-only.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
