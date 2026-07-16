import "server-only";

import { getJson, sendJson } from "./client";
import type {
  VockyMintedCredential,
  VockyProject,
  VockyProjectUsage,
  VockyUsage,
} from "./types";

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

// ── /app/projects/{id} — the per-project drill-down (P4.S4) ─────────────────
// Path ids are `encodeURIComponent`d: they reach us as raw route params, and a
// malformed one must produce a clean 400/404 from vocky rather than a mangled
// path. Reads take an optional `signal`; writes do not (they are server actions,
// not cancellable renders).

/**
 * `GET /app/projects/{id}` (bearer) → 200 `{project}`.
 *
 * Reuses the `POST /app/projects` envelope — vocky wraps both in `{project}`.
 *
 * THREE failure statuses, all meaningful to the caller:
 *   - 400 — `id` is not a UUID;
 *   - 404 — the project is missing OR belongs to another tenant. vocky answers
 *     404-never-403 on purpose (`_load_scoped_project`), so project ids can
 *     never be probed across tenants; the UI must preserve that by rendering
 *     the same not-found page for both.
 */
export async function getProject(
  token: string,
  projectId: string,
  signal?: AbortSignal,
): Promise<VockyProject> {
  const raw = await getJson<RawProjectResponse>(
    `/app/projects/${encodeURIComponent(projectId)}`,
    { token, signal },
  );
  return raw.project;
}

/**
 * `POST /app/projects/{id}/credentials` (bearer) `{name?}` → 201
 * `{credential, key}`.
 *
 * Returns the envelope WHOLE (`VockyMintedCredential`), unlike every other call
 * here: `key` is the PLAINTEXT `vk_…` credential and vocky returns it EXACTLY
 * ONCE (only `sha256_hex(key)` + `key[:12]` are persisted), so unwrapping to
 * `credential` would silently discard the only copy in existence. The caller
 * owns the secret from here: show it once, never log it, never persist it.
 *
 * `name` is OPTIONAL — vocky's `CreateCredentialInput` defaults it to `null` and
 * accepts an empty body — so an omitted name sends `{}` rather than `{name: null}`
 * or `{name: ""}`. vocky measures the 200-char limit BEFORE stripping and maps a
 * blank/whitespace name to `null` (never a 400, unlike project names).
 */
export async function createCredential(
  token: string,
  projectId: string,
  name?: string,
): Promise<VockyMintedCredential> {
  return sendJson<VockyMintedCredential>(
    `/app/projects/${encodeURIComponent(projectId)}/credentials`,
    "POST",
    name === undefined ? {} : { name },
    { token },
  );
}

/**
 * `DELETE /app/projects/{id}/credentials/{cid}` (bearer) → 204, empty body.
 *
 * Revoke is a STAMP, not a delete: vocky sets `revoked_at` and the credential
 * stays listed. 404 when the credential does not belong to the scoped project
 * (so foreign credential ids cannot be probed or revoked), 400 on a malformed
 * id, 404 on a foreign project id.
 *
 * `sendJson<void>` is the `auth.ts::logout` idiom — `parseBody` maps the 204 to
 * `undefined`, so there is nothing to unwrap.
 */
export async function revokeCredential(
  token: string,
  projectId: string,
  credentialId: string,
): Promise<void> {
  await sendJson<void>(
    `/app/projects/${encodeURIComponent(projectId)}/credentials/${encodeURIComponent(credentialId)}`,
    "DELETE",
    undefined,
    { token },
  );
}

/**
 * `GET /app/projects/{id}/usage` (bearer) → 200
 * `{window, totals, daily_counts, credentials}`.
 *
 * Called BARE, exactly like `getUsage`: vocky defaults the window to the last 30
 * days and echoes the resolved bounds back in `window`.
 *
 * No envelope (the payload IS the response) and no `project` object — hence the
 * separate `getProject` call for the page header. It DOES carry `credentials`,
 * serialized by the very same `serialize_credential` as the standalone list
 * route, which is why the project page needs no separate credentials call.
 *
 * Unlike `/app/usage`, `daily_counts` here is never `[]`; see `VockyProjectUsage`.
 */
export async function getProjectUsage(
  token: string,
  projectId: string,
  signal?: AbortSignal,
): Promise<VockyProjectUsage> {
  return getJson<VockyProjectUsage>(
    `/app/projects/${encodeURIComponent(projectId)}/usage`,
    { token, signal },
  );
}
