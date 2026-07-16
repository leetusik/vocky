import "server-only";

import { createHash, createCipheriv, createDecipheriv, randomBytes } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { readSessionEnv } from "./env";

// P4.S2 — the sealed-cookie session (D-P4-2). vocky issues an opaque 30-day
// bearer token from `/auth/*`; the BFF SEALS that token into an httpOnly cookie
// the Next.js app sets for ITSELF, so the raw vocky token never reaches browser
// JS and there is no web-side session store. This module is the whole crypto +
// guard surface; adapted from hi2vi_web's `src/lib/agent/auth.ts` — but where
// hi2vi HMAC-SIGNS a self-minted token, we AES-256-GCM ENCRYPT vocky's token
// (the GCM tag doubles as the integrity check) and the guards RETURN the
// decrypted token for bearer injection into server-to-server vocky calls.
//
// `import "server-only"` guarantees no `"use client"` module can pull the key or
// a live token into the browser bundle. `node:crypto` only ⇒ the routes/layouts
// that use this run on the nodejs runtime (never Edge). The key/token/cookie are
// never logged.

/** Cookie name holding the sealed vocky session. */
export const SESSION_COOKIE = "vocky_session";

/** Session lifetime: 30 days — matches vocky's opaque-token TTL exactly. */
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;
const SESSION_TTL_SECONDS = SESSION_TTL_MS / 1000;

/** Sealed-cookie envelope version — `v1.<iv>.<ct>.<tag>`, each part base64url. */
const SEAL_VERSION = "v1";

const LOGIN_PATH = "/login";

/** Sealed plaintext: the vocky token + its self-describing expiry (epoch ms). */
interface SealedPayload {
  token: string;
  exp: number;
}

/** Cookie attributes (Secure only in prod — dev is plain http on 127.0.0.1). */
export interface SessionCookieOptions {
  httpOnly: true;
  sameSite: "strict";
  secure: boolean;
  path: "/";
  maxAge: number;
}

/** The Set-Cookie attributes used when issuing the session (login/signup). */
export function sessionCookieOptions(): SessionCookieOptions {
  return {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  };
}

/** The Set-Cookie attributes used when clearing the session (logout) — maxAge 0. */
export function clearedSessionCookieOptions(): SessionCookieOptions {
  return { ...sessionCookieOptions(), maxAge: 0 };
}

/** Derive the 32-byte AES-256 key from SESSION_SECRET (sha256). */
function sessionKey(): Buffer {
  const { SESSION_SECRET } = readSessionEnv();
  return createHash("sha256").update(SESSION_SECRET).digest();
}

/**
 * Seal a vocky bearer token into the cookie value `v1.<iv>.<ct>.<tag>` (each part
 * base64url). Plaintext is JSON `{token, exp}` where `exp = now + 30d`; a fresh
 * random 12-byte IV is generated per seal. Reads SESSION_SECRET (throws naming the
 * key, not its value, when unset → the caller turns that into a clean 500).
 */
export function sealSession(token: string, now: number = Date.now()): string {
  const payload: SealedPayload = { token, exp: now + SESSION_TTL_MS };
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", sessionKey(), iv);
  const ct = Buffer.concat([
    cipher.update(JSON.stringify(payload), "utf8"),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();
  return [
    SEAL_VERSION,
    iv.toString("base64url"),
    ct.toString("base64url"),
    tag.toString("base64url"),
  ].join(".");
}

/**
 * Open a sealed cookie value and return the vocky token, or `null` for ANY
 * failure — wrong shape/version, a decrypt/tag-verify failure (tampering), a
 * non-JSON payload, or an expired `exp`. The GCM auth tag makes tampering a
 * decrypt failure, so a flipped byte can never yield a forged token. Never
 * throws, so callers can treat "no valid session" uniformly.
 */
export function openSession(
  value: string | undefined | null,
  now: number = Date.now(),
): string | null {
  if (!value) return null;
  const parts = value.split(".");
  if (parts.length !== 4) return null;
  const [version, ivB64, ctB64, tagB64] = parts;
  if (version !== SEAL_VERSION) return null;

  try {
    const iv = Buffer.from(ivB64, "base64url");
    const ct = Buffer.from(ctB64, "base64url");
    const tag = Buffer.from(tagB64, "base64url");
    if (iv.length !== 12 || tag.length !== 16 || ct.length === 0) return null;

    const decipher = createDecipheriv("aes-256-gcm", sessionKey(), iv);
    decipher.setAuthTag(tag);
    // `final()` throws if the tag does not verify → tampering caught here.
    const pt = Buffer.concat([decipher.update(ct), decipher.final()]).toString(
      "utf8",
    );
    const payload = JSON.parse(pt) as Partial<SealedPayload>;
    if (
      typeof payload.token !== "string" ||
      payload.token === "" ||
      typeof payload.exp !== "number" ||
      !Number.isFinite(payload.exp) ||
      payload.exp <= now
    ) {
      return null;
    }
    return payload.token;
  } catch {
    return null;
  }
}

/**
 * Read the raw session cookie value out of a `Request` (used by the logout route,
 * a pure function of the incoming request rather than the async `cookies()` store).
 */
export function readSessionCookie(req: Request): string | undefined {
  const header = req.headers.get("cookie");
  if (!header) return undefined;
  for (const part of header.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq).trim() === SESSION_COOKIE) {
      return decodeURIComponent(part.slice(eq + 1).trim());
    }
  }
  return undefined;
}

/**
 * Server-component/layout guard (no redirect): read the sealed cookie via the
 * async `cookies()` store and return the vocky token, or `null` when it is
 * absent/invalid/expired. Reading the cookie opts the caller into dynamic
 * rendering (never statically prerendered).
 */
export async function getSession(): Promise<string | null> {
  const store = await cookies();
  return openSession(store.get(SESSION_COOKIE)?.value);
}

/**
 * Server-component/layout guard that REQUIRES a session: returns the decrypted
 * vocky token for bearer injection, or `redirect("/login")` when the cookie is
 * absent/invalid/expired. The `(app)` layout awaits this before rendering.
 */
export async function requireSession(): Promise<string> {
  const token = await getSession();
  if (!token) redirect(LOGIN_PATH);
  return token;
}

/**
 * CSRF defense-in-depth for the BFF mutation routes (ported verbatim from
 * hi2vi_web): accept when `Sec-Fetch-Site` is `same-origin`/`none`, or when the
 * `Origin` header's host matches the request `Host`. Anything else — a cross-site
 * fetch, a mismatched Origin, or no origin signal at all — is rejected (the
 * caller returns 403). SameSite=Strict already blunts CSRF; this is the second layer.
 */
export function assertSameOrigin(req: Request): boolean {
  const secFetchSite = req.headers.get("sec-fetch-site");
  if (secFetchSite === "same-origin" || secFetchSite === "none") {
    return true;
  }
  const origin = req.headers.get("origin");
  if (origin) {
    try {
      const host = req.headers.get("host");
      if (host && new URL(origin).host === host) return true;
    } catch {
      // malformed Origin → fall through to reject
    }
  }
  return false;
}
