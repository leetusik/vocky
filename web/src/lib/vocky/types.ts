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
 * NOTE: vocky enforces NO uniqueness on `name` — two projects in the same tenant
 * may legitimately share one. Anything rendering a list of these MUST key on
 * `id`, never on `name`.
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
