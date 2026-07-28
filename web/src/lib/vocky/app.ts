import "server-only";

import { getJson, sendJson } from "./client";
import type {
  VockyCredential,
  VockyFeedbackDetail,
  VockyFeedbackPage,
  VockyFeedbackQuery,
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
 * GET-OR-CREATE, idempotent on name (P10.S1): `projects` now carries
 * `UNIQUE(tenant_id, name)`, and a name that already exists in the caller's org
 * returns the EXISTING row rather than erroring. Always answers 201 either way,
 * so a caller cannot tell "created" from "already existed" from the status
 * alone.
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

// ── /app/feedback — the cross-project read + search surface (P4.S5) ─────────
// READ ONLY. Feedback MANAGEMENT (edit/delete/comment) lives on the `vk_`-keyed
// `/api/project/feedback` surface — a different credential entirely — and is out
// of scope for this app, so there is no `updateFeedback` here to add later.

/** The `GET /app/feedback/{id}` envelope. */
interface RawFeedbackDetailResponse {
  record: VockyFeedbackDetail;
}

/**
 * Build the `?…` suffix for `listFeedback`, or `""` when nothing is active.
 *
 * The app's FIRST query string, so the rules it settles:
 *   - BLANK IS OMITTED, NEVER SENT. vocky collapses a blank text filter to "no
 *     filter", but `tag` and `cursor` REJECT blank with a 400 (`normalize_tag` /
 *     `decode_cursor`), and `project_id`/`feedback_value`/`limit` 400 on an
 *     unparseable value — so a blank param is never merely redundant, it is a
 *     failure waiting to happen. A GET form necessarily submits its empty fields
 *     (`?q=&project_id=`), which makes this the common case, not the edge case.
 *   - Values are trimmed to match vocky's own normalization, so the URL and the
 *     filter vocky applies never disagree.
 *   - `URLSearchParams` does ALL the escaping. Do NOT `encodeURIComponent` on top
 *     of it — that double-encodes (`결제` → `%25EA%25B2%25B0…`) and silently
 *     searches for the literal escape text. It encodes a space as `+`, which
 *     Starlette decodes back to a space correctly.
 *   - No params ⇒ the path stays BARE (`/app/feedback`, no trailing `?`).
 */
function feedbackQueryString(params: VockyFeedbackQuery): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    const raw = typeof value === "string" ? value.trim() : String(value);
    if (raw === "") continue;
    search.set(key, raw);
  }
  const query = search.toString();
  return query === "" ? "" : `?${query}`;
}

/**
 * `GET /app/feedback` (bearer) → 200 `{records, next_cursor?}` — feedback across
 * ALL the caller's tenant's projects, newest-first (`ingested_at DESC, id DESC`)
 * and keyset-paged.
 *
 * Takes an OPTIONS OBJECT, unlike every other call in this file (which take
 * scalars): vocky accepts 16 optional filters, and threading those positionally
 * would be unreadable and unsafe at every call site.
 *
 * TWO THINGS THAT BITE:
 *   - `next_cursor` is an OMITTED KEY when the page is exhausted, never `null`.
 *     "More pages?" is `next_cursor !== undefined`; a `!== null` test reads true
 *     forever and pages endlessly.
 *   - THE CURSOR DOES NOT ENCODE THE FILTERS. It carries only `{ingested_at, id}`,
 *     so a next-page call MUST resend every active filter or the scope silently
 *     widens mid-pagination.
 *
 * A tenant with no projects (or a scope that resolves to none) answers
 * `{records: []}` without touching the DB. `project_id` narrows the scope: a
 * malformed one is a 400, one the tenant does not own is a 404 (never 403).
 */
export async function listFeedback(
  token: string,
  params: VockyFeedbackQuery = {},
  signal?: AbortSignal,
): Promise<VockyFeedbackPage> {
  const page = await getJson<VockyFeedbackPage>(
    `/app/feedback${feedbackQueryString(params)}`,
    { token, signal },
  );
  // Spread-then-default: preserves the ABSENCE of `next_cursor` (spreading a
  // missing key never creates it) while defending `records`, which vocky always
  // sends. Rebuilding the object field-by-field would materialize
  // `next_cursor: undefined` and blur "exhausted" into "present but empty".
  return { ...page, records: page.records ?? [] };
}

/**
 * `GET /app/feedback/{id}` (bearer) → 200 `{record: {…, comments, attachments}}`.
 *
 * WRAPPED in `{record}` — unlike the list, whose `records` arrives bare. The
 * record is the same `_serialize_app_record` shape plus nested `comments[]` and
 * `attachments[]`.
 *
 * 400 (not a UUID) / 404 (missing OR outside the caller's tenant, including
 * legacy NULL-project rows — 404-never-403, so ids cannot be probed) / 500
 * (storage read failure). Callers map 400+404 to the same not-found page and
 * rethrow the rest.
 *
 * Each attachment's `url` is a VOCKY-relative path needing the session bearer —
 * not something a browser can fetch. The web app proxies it instead; see
 * `app/api/app/feedback/[feedbackId]/attachments/[attachmentId]/route.ts`.
 */
export async function getFeedbackDetail(
  token: string,
  feedbackId: string,
  signal?: AbortSignal,
): Promise<VockyFeedbackDetail> {
  const raw = await getJson<RawFeedbackDetailResponse>(
    `/app/feedback/${encodeURIComponent(feedbackId)}`,
    { token, signal },
  );
  return raw.record;
}

// ── /app/credentials — the org-level key surface (P10.S4) ───────────────────
// Additive beside the per-project `/app/projects/{id}/credentials` routes
// above: an org-level key (`project_id: null`) authorizes capture, read, and
// manage across every project in the caller's org. The two listings are
// disjoint in both directions, so a tenant's keys enumerate exactly once
// across the two surfaces.

/** The `GET /app/credentials` envelope. */
interface RawOrgCredentialsResponse {
  credentials?: VockyCredential[];
}

/**
 * `GET /app/credentials` (bearer) → 200 `{credentials: [...]}` — the caller's
 * tenant's ORG-LEVEL credentials only (`project_id IS NULL`), oldest-first,
 * INCLUDING revoked (revoke is a stamp, not a delete — same as the per-project
 * list). Never includes a project-bound credential.
 *
 * The `?? []` is defensive only — vocky always sends the key.
 */
export async function listOrgCredentials(
  token: string,
  signal?: AbortSignal,
): Promise<VockyCredential[]> {
  const raw = await getJson<RawOrgCredentialsResponse>("/app/credentials", {
    token,
    signal,
  });
  return raw.credentials ?? [];
}

/**
 * `POST /app/credentials` (bearer) `{name?}` → 201 `{credential, key}` — mints
 * an ORG-LEVEL key (`project_id: null` on the returned credential).
 *
 * Returns the envelope WHOLE (`VockyMintedCredential`), exactly like
 * `createCredential` above: `key` is the PLAINTEXT `vk_…` credential and vocky
 * returns it EXACTLY ONCE (only its sha256 hash is persisted), so unwrapping
 * to `credential` would discard the only copy in existence.
 *
 * `name` is OPTIONAL, same rules as the per-project mint: an omitted name
 * sends `{}` (never `{name: null}`), and vocky maps a blank/whitespace name to
 * `null` rather than a 400.
 */
export async function createOrgCredential(
  token: string,
  name?: string,
): Promise<VockyMintedCredential> {
  return sendJson<VockyMintedCredential>(
    "/app/credentials",
    "POST",
    name === undefined ? {} : { name },
    { token },
  );
}

/**
 * `DELETE /app/credentials/{id}` (bearer) → 204, empty body.
 *
 * 404-never-403, and NARROWER than the per-project delete: vocky 404s unless
 * the row is BOTH the caller's tenant AND org-level — so a project-bound
 * credential of the caller's OWN tenant also 404s here; it can only be revoked
 * through `/app/projects/{id}/credentials/{cid}`. 400 on a malformed id.
 */
export async function revokeOrgCredential(
  token: string,
  credentialId: string,
): Promise<void> {
  await sendJson<void>(
    `/app/credentials/${encodeURIComponent(credentialId)}`,
    "DELETE",
    undefined,
    { token },
  );
}
