import "server-only";

// P4.S2 — server-only environment readers for the BFF.
//
// Adapted from hi2vi_web's `src/lib/agent/env.ts` `readEnvGroup` convention: a
// typed reader that throws a single Error naming every missing (unset/blank) key
// and NEVER its value. `import "server-only"` above means any `"use client"`
// module that ever imports this file fails the build loudly — the session secret
// and the internal vocky base URL can never reach the browser bundle. Neither key
// is `NEXT_PUBLIC_`.
//
// Grouped PER CONSUMER (like hi2vi): the vocky client reads only VOCKY_API_BASE_URL,
// the session layer reads only SESSION_SECRET, so one missing key never gates the
// other subsystem. Reads happen lazily inside these functions (never at module
// top-level) so `next build` — which does not run the request path — needs no env.

/**
 * Read a group of required env vars, returning a typed record. Throws a single
 * Error naming every missing (unset or blank) key — never a value.
 */
function readEnvGroup<K extends string>(
  label: string,
  keys: readonly K[],
): Record<K, string> {
  const missing: K[] = [];
  const config = {} as Record<K, string>;
  for (const key of keys) {
    const value = process.env[key];
    if (typeof value !== "string" || value.trim() === "") {
      missing.push(key);
    } else {
      config[key] = value.trim();
    }
  }
  if (missing.length > 0) {
    throw new Error(
      `web env: missing ${label} env vars: ${missing.join(", ")}`,
    );
  }
  return config;
}

const VOCKY_API_KEYS = ["VOCKY_API_BASE_URL"] as const;
const SESSION_KEYS = ["SESSION_SECRET"] as const;

export type VockyApiEnv = Record<(typeof VOCKY_API_KEYS)[number], string>;
export type SessionEnv = Record<(typeof SESSION_KEYS)[number], string>;

/**
 * Base URL of the vocky API the Next.js server calls server-to-server, e.g.
 * `http://127.0.0.1:8000`. Server-only — the browser never sees it (the BFF is
 * the only client). A trailing slash is stripped by the vocky client.
 */
export function readVockyApiEnv(): VockyApiEnv {
  return readEnvGroup("vocky API", VOCKY_API_KEYS);
}

/**
 * Secret from which the AES-256-GCM session key is derived (`sha256(SESSION_SECRET)`).
 * Server-only; rotating it invalidates every live sealed cookie (forces re-login).
 */
export function readSessionEnv(): SessionEnv {
  return readEnvGroup("session", SESSION_KEYS);
}
