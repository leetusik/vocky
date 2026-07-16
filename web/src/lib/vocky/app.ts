import "server-only";

import { getJson, sendJson } from "./client";
import type { VockyProject, VockyUsage } from "./types";

// P4.S3 — typed server-side calls against vocky's session-scoped `/app/*`
// surface, the sibling of `auth.ts` (which is scoped to `/auth/*`). Both sit on
// the same `client.ts` seam: the caller passes the vocky bearer token unsealed
// from the httpOnly cookie by `requireIdentity()`, and every call is
// `cache: "no-store"` by construction.
//
// Every function here takes the `token` as a REQUIRED POSITIONAL argument (the
// shape `me()` established): these routes are all guarded by vocky's
// `require_user`, so an unauthenticated call is never meaningful. Errors surface
// as `ApiError` carrying the STATUS — callers branch on that, never on vocky's
// `detail` text.

/** The `GET /app/projects` envelope. */
interface RawProjectsResponse {
  projects?: VockyProject[];
}

/** The `POST /app/projects` envelope. */
interface RawProjectResponse {
  project: VockyProject;
}

/**
 * `GET /app/projects` (bearer) → 200 `{projects: [...]}`, the caller's tenant's
 * projects OLDEST-FIRST and unpaginated. A tenant with no projects answers
 * `{projects: []}`.
 *
 * The `?? []` is defensive only — vocky always sends the key.
 */
export async function listProjects(
  token: string,
  signal?: AbortSignal,
): Promise<VockyProject[]> {
  const raw = await getJson<RawProjectsResponse>("/app/projects", {
    token,
    signal,
  });
  return raw.projects ?? [];
}

/**
 * `POST /app/projects` (bearer) `{name}` → 201 `{project}`.
 *
 * vocky validates `name` as 1–200 chars and stores it TRIMMED, but measures the
 * length BEFORE trimming and rejects an all-whitespace name — so `"   "` is a
 * 400, not an empty-string store. Callers validate their own input first and map
 * a 400 by status.
 *
 * Duplicate names are ALLOWED (no uniqueness constraint anywhere in vocky), so
 * this can legitimately return a project whose `name` matches an existing one.
 */
export async function createProject(
  token: string,
  name: string,
): Promise<VockyProject> {
  const raw = await sendJson<RawProjectResponse>(
    "/app/projects",
    "POST",
    { name },
    { token },
  );
  return raw.project;
}

/**
 * `GET /app/usage` (bearer) → 200 `{window, totals, daily_counts, projects}`.
 *
 * Called BARE: vocky defaults the window to the last 30 days when both bounds
 * are omitted, and echoes the resolved window back in `window` — which is what
 * the UI labels off, rather than recomputing the default.
 *
 * No envelope to unwrap (unlike the two above) — the payload IS the response.
 * Beware `daily_counts: []` on a tenant with zero projects; see `VockyUsage`.
 */
export async function getUsage(
  token: string,
  signal?: AbortSignal,
): Promise<VockyUsage> {
  return getJson<VockyUsage>("/app/usage", { token, signal });
}
