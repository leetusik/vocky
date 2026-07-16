import "server-only";

import { NextResponse } from "next/server";
import { z } from "zod";

import { clientIp } from "./client-ip";
import { checkRateLimit } from "./rate-limit";
import {
  assertSameOrigin,
  sealSession,
  SESSION_COOKIE,
  sessionCookieOptions,
} from "./session";
import { ApiError } from "./vocky/client";
import type { VockySession } from "./vocky/types";

// P4.S2 — the shared BFF credential pipeline behind `POST /api/auth/login` and
// `POST /api/auth/signup`. Login and signup differ ONLY in their throttle numbers,
// which vocky call they make, and which vocky statuses are meaningful to the
// client — so the ordered security checks live here ONCE, audited in one place,
// rather than being duplicated (and drifting) across two routes.
//
// The order is hi2vi_web's, cheapest/most-hostile rejection first:
//   1. JSON only                      → 415
//   2. same-origin (CSRF layer 2)     → 403
//   3. per-IP rate limit              → 429   (BEFORE parsing, so a flood is cheap)
//   4. parse + zod-validate           → 400 (malformed JSON) / 422 (bad shape)
//   5. call vocky server-to-server    → mapped status, detail text NEVER echoed
//   6. seal the vocky token → cookie  → 200
//
// The response body is only ever `{ok}` — the client keys off the STATUS CODE, so
// vocky's `detail` (and its unknown-email/bad-password indistinguishability) never
// leaks through this boundary. Passwords are never logged, in any branch.

/** JSON body, never cached. `{ok}` is the only field the client reads. */
export function json(status: number, body: Record<string, unknown>): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

/**
 * Request-body shape. Deliberately permissive beyond presence/typing: vocky owns
 * the real credential rules (email normalization + the 8-char password minimum)
 * and answers 400, which we pass through — so the BFF never forks from the
 * backend's validation. The max lengths are only a cheap DoS guard.
 */
const credentialsSchema = z.object({
  email: z.string().min(1).max(320),
  password: z.string().min(1).max(1024),
});

export interface CredentialRouteOptions {
  /** Throttle: max attempts per IP per `windowMs`. */
  limit: number;
  windowMs: number;
  /**
   * Rate-limit bucket namespace, e.g. `"auth-login"`. REQUIRED and distinct per
   * route: the limiter keys on this string, so sharing a bare IP key would let
   * login attempts consume the signup budget (and vice-versa).
   */
  bucket: string;
  /** The vocky call — `signup` or `login` from `@/lib/vocky/auth`. */
  call: (email: string, password: string) => Promise<VockySession>;
  /**
   * vocky statuses that are meaningful to the client and pass through verbatim
   * (login: 401 + 400; signup: 409 + 400). Any OTHER vocky error becomes a 502 —
   * an upstream fault is never reported as if it were the user's mistake.
   */
  passThroughStatuses: readonly number[];
}

/**
 * Run the ordered credential pipeline and, on success, seal vocky's bearer token
 * into the httpOnly session cookie on a 200. Returns the `Response` the route
 * handler returns directly.
 */
export async function handleCredentialRoute(
  req: Request,
  options: CredentialRouteOptions,
): Promise<Response> {
  // 1. Only JSON (415) — cheap reject + a basic CSRF blunt (a cross-site form
  //    POST cannot set application/json without preflight).
  const contentType = req.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return json(415, { ok: false });
  }

  // 2. Same-origin only (403) — CSRF defense in depth (SameSite=Strict + this).
  if (!assertSameOrigin(req)) {
    return json(403, { ok: false });
  }

  // 3. Per-IP rate limit (429) BEFORE parsing/hashing, so a flood is cheap to shed.
  const ip = clientIp(req.headers);
  if (
    !checkRateLimit(`${options.bucket}:${ip}`, options.limit, options.windowMs).ok
  ) {
    return json(429, { ok: false });
  }

  // 4. Parse the body (400 malformed JSON) and validate the shape (422).
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return json(400, { ok: false });
  }
  const parsed = credentialsSchema.safeParse(raw);
  if (!parsed.success) {
    return json(422, { ok: false });
  }
  const email = parsed.data.email.trim();
  const { password } = parsed.data;
  if (email === "") {
    return json(422, { ok: false });
  }

  // 5. Call vocky server-to-server. Its `detail` text is NEVER echoed: a
  //    meaningful status passes through bare, anything else is an upstream fault.
  let session: VockySession;
  try {
    session = await options.call(email, password);
  } catch (error) {
    if (error instanceof ApiError) {
      if (options.passThroughStatuses.includes(error.status)) {
        return json(error.status, { ok: false });
      }
      return json(502, { ok: false });
    }
    // Missing env or a transport failure — never surface the cause to the client.
    return json(500, { ok: false });
  }

  // 6. Success → seal vocky's opaque token into the httpOnly cookie. The token
  //    itself is never returned to the browser; only the sealed envelope is.
  let sealed: string;
  try {
    sealed = sealSession(session.token);
  } catch {
    // SESSION_SECRET unset/unreadable → clean 500, never a leak.
    return json(500, { ok: false });
  }
  const res = json(200, { ok: true });
  res.cookies.set(SESSION_COOKIE, sealed, sessionCookieOptions());
  return res;
}
