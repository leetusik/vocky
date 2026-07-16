import { json } from "@/lib/bff";
import {
  assertSameOrigin,
  clearedSessionCookieOptions,
  openSession,
  readSessionCookie,
  SESSION_COOKIE,
} from "@/lib/session";
import { logout } from "@/lib/vocky/auth";

// P4.S2 — BFF logout. Two halves, in this order:
//   1. best-effort: unseal the current cookie and revoke the token at vocky
//      (`POST /auth/logout`, 204/idempotent/never-401, errors swallowed);
//   2. unconditionally clear the sealed cookie on a 200.
//
// The cookie clear is what actually ends the browser session, so it happens even
// when vocky is unreachable or the cookie was already invalid — logout must never
// be able to fail open. Same-origin only (CSRF defense in depth); nodejs runtime +
// no cache to match the rest of the auth surface.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request): Promise<Response> {
  if (!assertSameOrigin(req)) {
    return json(403, { ok: false });
  }

  // Revoke server-side when we still hold a live token. `openSession` returns null
  // for an absent/tampered/expired cookie — nothing to revoke, so skip straight to
  // clearing. `logout()` is fire-and-forget and never throws.
  const token = openSession(readSessionCookie(req));
  if (token) {
    await logout(token);
  }

  const res = json(200, { ok: true });
  res.cookies.set(SESSION_COOKIE, "", clearedSessionCookieOptions());
  return res;
}
