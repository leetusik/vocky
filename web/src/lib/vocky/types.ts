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
