import "server-only";

import { cache } from "react";
import { redirect } from "next/navigation";

import { getSession, requireSession } from "./session";
import { me } from "./vocky/auth";
import { ApiError } from "./vocky/client";
import type { VockyIdentity } from "./vocky/types";

// P4.S2 — the composed page guards, one layer above `session.ts` (cookie/crypto)
// and `vocky/auth.ts` (the API calls). `session.ts` deliberately knows nothing
// about vocky and vice-versa; this module is where the two meet.

const DASHBOARD_PATH = "/dashboard";
const LOGIN_PATH = "/login";

export interface AuthenticatedContext {
  /** The vocky bearer token, unsealed from the cookie — for server-to-server calls. */
  token: string;
  identity: VockyIdentity;
}

/**
 * The `(app)` route-group guard: require a sealed session, then confirm it is
 * still LIVE at vocky (`GET /auth/me`) and return the caller's identity + token.
 *
 * Two distinct failures, two distinct handlings:
 *   - no/invalid/expired cookie → `requireSession()` redirects to /login;
 *   - a cookie whose vocky token is dead (revoked/expired server-side) → vocky
 *     answers 401 and we redirect to /login. We cannot CLEAR the cookie here
 *     (Next only allows cookie writes from route handlers / server actions), so
 *     the stale cookie survives — which is exactly why `redirectIfAuthenticated`
 *     below re-verifies rather than trusting the cookie alone. A successful login
 *     overwrites it; `POST /api/auth/logout` clears it.
 * Any OTHER error (vocky down, transport failure) is rethrown rather than
 * silently logging the user out — an outage should surface, not masquerade as
 * a session expiry.
 *
 * `cache()` dedupes this per request, so a layout + its page both calling it cost
 * ONE `/auth/me` round-trip.
 */
export const requireIdentity = cache(
  async (): Promise<AuthenticatedContext> => {
    const token = await requireSession();
    try {
      return { token, identity: await me(token) };
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        redirect(LOGIN_PATH);
      }
      throw error;
    }
  },
);

/**
 * The `(auth)` page bounce: send an already-signed-in visitor to the dashboard.
 *
 * It VERIFIES the token against vocky before bouncing, on purpose. Checking only
 * the cookie would ping-pong forever in the revoked-token case: /login sees a
 * crypto-valid cookie → /dashboard → the guard's `/auth/me` 401s → back to /login
 * → … Verifying breaks that loop — a dead cookie simply renders the login form,
 * and signing in overwrites it.
 */
export async function redirectIfAuthenticated(): Promise<void> {
  const token = await getSession();
  if (!token) return;
  const identity = await me(token).catch(() => null);
  if (identity) redirect(DASHBOARD_PATH);
}
