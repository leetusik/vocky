"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { CREATE_PROJECT_ERRORS } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { createProject } from "@/lib/vocky/app";
import { ApiError } from "@/lib/vocky/client";

/**
 * P4.S3 — create-project as a SERVER ACTION, the architectural rule for authed
 * mutations in this app (S4's credential mint/revoke follows it too).
 *
 * Why not a route handler + client fetch, like S2's auth surface? Because the two
 * cases are genuinely different. S2's `/api/auth/*` routes exist for a PUBLIC,
 * UNAUTHENTICATED, rate-limited surface that has to do its own origin check and
 * throttling before anyone is identified. This mutation sits behind
 * `requireIdentity()`, gets Next's built-in server-action CSRF protection for
 * free, and can `revalidatePath` the very page that renders the result — a route
 * handler would add a hand-rolled fetch, a second origin check, and a manual
 * refresh for no benefit.
 *
 * The token never reaches the browser: it is unsealed from the httpOnly cookie
 * inside this action and handed straight to the server-to-server vocky call.
 */

/**
 * Mirrors vocky's `CreateProjectInput` (1–200 chars) so the common mistakes are
 * caught without a round-trip. Two details are deliberate:
 *   - length is measured BEFORE trimming, exactly as vocky's pydantic model does
 *     (`Field(min_length=1, max_length=200)` runs before the `_strip_name`
 *     validator), so this and the backend agree on the boundary;
 *   - the trailing `.trim()` then rejects an all-whitespace name, which vocky's
 *     `_strip_name` also rejects as a 400.
 * vocky remains the authority — a 400 from it is still mapped below.
 */
const nameSchema = z
  .string()
  .min(1)
  .max(200)
  .refine((value) => value.trim().length > 0);

/**
 * NOTE: this file may export ONLY async functions — a `"use server"` module's
 * every export is registered as a callable server action, so exporting a plain
 * value makes Next throw "A 'use server' file can only export async functions"
 * at request time. (A TYPE export like this one is fine: types are erased before
 * the loader sees the module.) The form's initial state therefore lives in the
 * client island, not here.
 */
export interface CreateProjectState {
  /** Display copy for a failure, or `null` on success / first render. */
  error: string | null;
  /** Bumped on each success so the client island can reset the field. */
  ok?: number;
}

/**
 * `useActionState` action: validate → `POST /app/projects` → revalidate.
 *
 * Failures map by HTTP STATUS, never by vocky's `detail` text (the `AUTH_ERRORS`
 * idiom from `content/auth.ts`) — the text is a backend implementation detail.
 * A 401 here means the session died mid-request; the message says so and the next
 * navigation hits the `(app)` guard and bounces to /login.
 */
export async function createProjectAction(
  _prevState: CreateProjectState,
  formData: FormData,
): Promise<CreateProjectState> {
  const parsed = nameSchema.safeParse(formData.get("name"));
  if (!parsed.success) {
    return { error: CREATE_PROJECT_ERRORS.invalidName };
  }

  // OUTSIDE the try on purpose: `requireIdentity()` signals "no session" by
  // calling `redirect()`, which works by THROWING a control-flow error that Next
  // must see. Catching it here would swallow the redirect and render a bogus
  // "please try again" instead of bouncing to /login.
  const { token } = await requireIdentity();

  try {
    await createProject(token, parsed.data);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 400) return { error: CREATE_PROJECT_ERRORS.invalidName };
      if (error.status === 401) return { error: CREATE_PROJECT_ERRORS.sessionExpired };
    }
    return { error: CREATE_PROJECT_ERRORS.generic };
  }

  // The page re-fetches `/app/projects` + `/app/usage` on the next render, so the
  // new project (and its now-zero-filled usage series) appear without a manual
  // client-side refresh.
  revalidatePath("/dashboard");
  return { error: null, ok: Date.now() };
}
