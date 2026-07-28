// P4.S2 — shared shapes for vocky's `/auth/*` + `/app/*` JSON (server-side).
// Pure types, no runtime values — S3–S5 extend this file with the `/app/*`
// shapes (projects, credentials, usage, feedback) as they add those calls.
//
// These mirror vocky's serializers verbatim (`src/vocky/auth_api.py`
// `serialize_user` / `serialize_tenant`): ids are STRINGS (UUIDs stringified)
// and timestamps are ISO-8601 strings, never Date objects.

/** `serialize_user` — never carries `password_hash`. */
export interface VockyUser {
  id: string;
  email: string;
  created_at: string;
}

/** `serialize_tenant`. */
export interface VockyTenant {
  id: string;
  name: string;
  created_at: string;
}

/**
 * The normalized result of signup/login: the raw vocky bearer token (which the
 * BFF immediately seals into the cookie and never returns to the browser) plus
 * the caller's identity and their ACTIVE tenant.
 *
 * `tenant` is normalized across vocky's signup/login asymmetry — signup answers
 * `tenant` (singular), login answers `tenants[]` — matching vocky's own
 * `require_user`, which treats `tenants[0]` as the active tenant. It is `null`
 * only in the pathological zero-tenant case (signup always provisions one).
 */
export interface VockySession {
  token: string;
  user: VockyUser;
  tenant: VockyTenant | null;
}

/** `GET /auth/me` — identity without a token, tenant normalized as above. */
export interface VockyIdentity {
  user: VockyUser;
  tenant: VockyTenant | null;
  /** Every tenant the user belongs to, in vocky's order (`tenants[0]` = active). */
  tenants: VockyTenant[];
}

// ── `/app/*` shapes (P4.S3) ────────────────────────────────────────────────
// Mirroring `src/vocky/app_api.py::serialize_project` and
// `src/vocky/admin_api.py::serialize_metrics` / `serialize_metric_counts` /
// `serialize_daily_metric_count` (which `usage_api.py` reuses) verbatim.

/**
 * `serialize_project` — the canonical, full project shape from
 * `GET|POST /app/projects`.
 *
 * NOTE (P10.S1): `name` is now UNIQUE per tenant (`UNIQUE(tenant_id, name)`),
 * and `POST /app/projects` is get-or-create — a duplicate name returns the
 * EXISTING row rather than erroring. Anything rendering a list of these still
 * keys on `id`, never on `name`: that convention predates the constraint and
 * stays correct regardless of it.
 */
export interface VockyProject {
  id: string;
  name: string;
  tenant_id: string;
  created_at: string;
}

/**
 * `_serialize_usage_project` — the NARROWER project entry embedded in
 * `GET /app/usage`. Deliberately a separate type from `VockyProject`, not a
 * `Partial<>` or a shared interface: this serializer omits `tenant_id`, and
 * conflating the two would let a `usage.projects` entry be passed where the full
 * shape is required. The dashboard renders `/app/projects` (canonical) and
 * ignores this list.
 */
export interface VockyUsageProject {
  id: string;
  name: string;
  created_at: string;
}

/**
 * The resolved usage window, echoed back by vocky — ALWAYS read it from the
 * response rather than recomputing the default client-side. Both bounds are
 * instants (not date-only), so with the 30-day default the first and last daily
 * buckets cover PARTIAL days.
 */
export interface VockyUsageWindow {
  start_ingested_at: string;
  end_ingested_at: string;
}

/** `serialize_metric_counts` — `total` is the sum of the three rating buckets. */
export interface VockyMetricCounts {
  total: number;
  liked: number;
  disliked: number;
  unrated: number;
}

/** `serialize_daily_metric_count` — one day's bucket. */
export interface VockyDailyMetricCount {
  /** DATE-ONLY (`"2026-06-16"`), not a timestamp. Ascending across the series. */
  day: string;
  total: number;
  liked: number;
  disliked: number;
  unrated: number;
}

/**
 * `GET /app/usage` — the caller's whole-tenant capture volume (derived, never
 * metered — decision D-P3-5).
 *
 * ZERO-FILL IS CONDITIONAL: a tenant that owns at least one project gets a fully
 * zero-filled bucket per day of the window; a tenant with NO projects
 * short-circuits to `_zeroed_metrics()` and `daily_counts` is `[]`
 * (`usage_api.py::get_app_usage`). Consumers must handle the empty series
 * explicitly — never assume N buckets.
 */
export interface VockyUsage {
  window: VockyUsageWindow;
  totals: VockyMetricCounts;
  daily_counts: VockyDailyMetricCount[];
  projects: VockyUsageProject[];
}

// ── /app/projects/{id} shapes (P4.S4) ──────────────────────────────────────
// Mirroring `src/vocky/app_api.py::serialize_credential` and
// `src/vocky/usage_api.py::_project_usage_response` verbatim.

/**
 * `serialize_credential` — one project ingest key's METADATA. Never carries
 * `token_hash`, and never the plaintext key (see `VockyMintedCredential`).
 *
 * There is NO `status` field: a credential is Active exactly when
 * `revoked_at === null`, Revoked otherwise. Revoked credentials REMAIN listed
 * (vocky's revoke is a stamp, not a delete), so any consumer must derive the
 * state rather than assume the list is live-only.
 *
 * `token_prefix` is `key[:12]` — `"vk_"` plus the first 9 characters of the
 * opaque token. It is a DISPLAY STUB, not a usable credential.
 *
 * `project_id` (P10.S4): `null` means an ORG-LEVEL key — minted at
 * `POST /app/credentials` and authorizing capture/read/manage across every
 * project in the org, present and future. There is no separate scope field:
 * `project_id === null` IS the org-key signal. A consumer that needs a
 * project id for a project-BOUND credential should read it from the project
 * already in scope (e.g. the project-detail page's own `projectId`), never
 * from this field — it is absent exactly when the credential is org-level.
 */
export interface VockyCredential {
  id: string;
  /** `null` ⇔ org-level (spans every project in the org); see the doc above. */
  project_id: string | null;
  /** Optional display label; `null` when the key was minted unnamed. */
  name: string | null;
  token_prefix: string;
  created_at: string;
  /** Stamped on each ingest call; `null` until the key is first used. */
  last_used_at: string | null;
  /** `null` ⇔ Active. */
  revoked_at: string | null;
}

/**
 * `GET /app/projects/{id}/usage` — one project's capture volume plus that
 * project's credentials.
 *
 * A SEPARATE type from `VockyUsage`, not a shared/`Partial<>` one: this payload
 * has NO `projects` list and instead bundles `credentials` (the endpoint exists
 * to surface each key's `last_used_at`). The `window` / `totals` /
 * `daily_counts` fields come from the same `serialize_metrics` and are identical.
 *
 * Unlike `VockyUsage`, `daily_counts` is ALWAYS zero-filled here:
 * `_project_usage_response` has no zero-project short-circuit, so a project with
 * no captures still gets one bucket per day of the window rather than `[]`.
 */
export interface VockyProjectUsage {
  window: VockyUsageWindow;
  totals: VockyMetricCounts;
  daily_counts: VockyDailyMetricCount[];
  /** `serialize_credential` — the SAME serializer as the standalone list route. */
  credentials: VockyCredential[];
}

/**
 * `POST /app/projects/{id}/credentials` → 201 `{credential, key}` — the one
 * response that cannot be unwrapped to a single domain type.
 *
 * `key` is the PLAINTEXT `vk_…` credential, returned EXACTLY ONCE and never
 * recoverable: vocky persists only `sha256_hex(key)` + `key[:12]`. Unwrapping
 * this to a bare `VockyCredential` would throw away the only copy, so the
 * envelope is public and the caller is forced to decide what to do with the
 * secret. It must never be logged, put in a URL, or persisted.
 */
export interface VockyMintedCredential {
  credential: VockyCredential;
  key: string;
}

// ── /app/feedback shapes (P4.S5) ───────────────────────────────────────────
// Mirroring `src/vocky/app_feedback_api.py::_serialize_app_record` and the
// serializers it composes from `tools/query_feedback_common.py`
// (`serialize_record` / `serialize_comment` / `serialize_attachment`) verbatim.
//
// EVERY string field here is CALLER-SUPPLIED, UNTRUSTED text: it arrives from
// whatever service holds a `vk_` ingest key. Render it as text only — never
// through `dangerouslySetInnerHTML`, never as a URL/href.

/**
 * `_serialize_app_record` — one feedback record on the cross-project `/app/*`
 * surface: `serialize_record` PLUS `project_id`.
 *
 * A SUPERSET of the `/api/*` record, and so its own named type rather than a
 * shared/extended one (the house rule since `VockyUsageProject`): the `/api/*`
 * surface deliberately OMITS `project_id` — a project-credential caller already
 * knows its project — while a cross-project reader cannot tell the rows apart
 * without it.
 *
 * `project_id` is typed nullable because the serializer emits `null` for legacy
 * rows captured before projects existed. Those rows are UNREACHABLE here in
 * practice — the list filters by an owned-id set (SQL `IN` never matches NULL)
 * and get-one 404s them — but the type mirrors the serializer, not the filter.
 */
export interface VockyFeedback {
  id: string;
  /** The end user's feedback text. Always present (vocky requires it). */
  message: string;
  source_product: string;
  /** vocky's explicit-action rating: `1` = like, `2` = dislike, `null` = unrated. */
  feedback_value: 1 | 2 | null;
  comment: string | null;
  channel: string | null;
  source_integration: string | null;
  conversation_id: string | null;
  session_id: string | null;
  user_id: string | null;
  trigger_type: string | null;
  trigger_message: string | null;
  /** Free-form caller-supplied JSON object — no schema vocky enforces. */
  trigger_metadata: Record<string, unknown>;
  target_type: string | null;
  target_id: string | null;
  target_role: string | null;
  target_text: string | null;
  /** When the feedback HAPPENED (caller-reported, optional). */
  event_at: string | null;
  /** When vocky STORED it — the list's sort key (`ingested_at DESC, id DESC`). */
  ingested_at: string;
  tags: string[];
  /** Free-form caller-supplied JSON arrays — element shape is not vocky's to know. */
  messages: unknown[];
  used_context: unknown[];
  source_metadata: Record<string, unknown>;
  attributes: Record<string, unknown>;
  /** The `/app/*` addition; `null` only for legacy pre-project rows (see above). */
  project_id: string | null;
}

/** `serialize_comment` — an operator note on a record. Read-only on this surface. */
export interface VockyFeedbackComment {
  id: string;
  /** `null` when the comment was left unattributed. */
  author: string | null;
  body: string;
  created_at: string;
}

/** `serialize_attachment` — an uploaded file's METADATA (never its bytes). */
export interface VockyFeedbackAttachment {
  id: string;
  /** The STORED content type, i.e. whatever the uploader declared — untrusted. */
  content_type: string;
  byte_size: number;
  filename: string | null;
  created_at: string;
  /**
   * A VOCKY-RELATIVE path (`/app/feedback/{id}/attachments/{aid}`), not a URL the
   * browser can follow: fetching it needs the session bearer, which lives only on
   * our server. The browser gets our own proxy route instead — so this field is
   * never rendered into an `href` directly.
   */
  url: string;
}

/**
 * `GET /app/feedback/{id}` → the record WRAPPED in `{record}`, with its comments
 * and attachments nested. Note the asymmetry with the list, which returns
 * `records` BARE (no wrapper) — hence two different unwrapping rules in `app.ts`.
 */
export interface VockyFeedbackDetail extends VockyFeedback {
  comments: VockyFeedbackComment[];
  attachments: VockyFeedbackAttachment[];
}

/**
 * `GET /app/feedback` — one keyset-paged page, newest-first.
 *
 * `next_cursor` is OPTIONAL, never `null`: vocky OMITS the key entirely when the
 * page is exhausted (`if page.next_cursor is not None: payload[...] = ...`), so
 * "no more pages" is `next_cursor === undefined`. A `!== null` check would read
 * TRUE forever and page endlessly.
 */
export interface VockyFeedbackPage {
  records: VockyFeedback[];
  next_cursor?: string;
}

/**
 * The `GET /app/feedback` query — every param optional, vocky ignores unknown
 * ones. The UI surfaces only `q` / `project_id` / `feedback_value`; the rest stay
 * URL-reachable and are preserved across filtering + pagination.
 *
 * Sharp edges, all encoded in `listFeedback`'s param builder:
 *   - `tag` REJECTS blank with a 400 (`normalize_tag`), while every other text
 *     field collapses blank to "no filter" — so blanks are omitted, not sent;
 *   - `cursor` likewise 400s when blank;
 *   - `feedback_value` accepts ONLY 1 or 2 (never 0, never a bool);
 *   - `limit` is 1–100, defaulting to 50.
 */
export interface VockyFeedbackQuery {
  /** Case-insensitive SUBSTRING match over message+comment+target_text+trigger_message. */
  q?: string;
  project_id?: string;
  start_ingested_at?: string;
  end_ingested_at?: string;
  source_product?: string;
  source_integration?: string;
  conversation_id?: string;
  session_id?: string;
  user_id?: string;
  /** 1 = like, 2 = dislike. Anything else is a 400. */
  feedback_value?: 1 | 2;
  channel?: string;
  target_type?: "message" | "conversation" | "surface";
  trigger_type?:
    "like" | "dislike" | "comment" | "rating" | "survey" | "manual" | "other";
  /** Blank is a 400 here, unlike the other text filters. */
  tag?: string;
  /** 1–100; vocky defaults to 50. */
  limit?: number;
  /** Opaque base64url keyset cursor from a previous page's `next_cursor`. */
  cursor?: string;
}
