// Authenticated app-shell copy + nav (P4.S2). The shell is the chrome S3–S5 render
// inside; this is the single source for its labels and rail links.

export interface AppNavItem {
  label: string;
  href: string;
  /**
   * True when the destination route does not exist yet — rendered as a muted,
   * non-interactive rail item with a "Soon" tag instead of a link that 404s.
   * The slice that ships the route drops this flag.
   */
  soon?: boolean;
}

/**
 * Rail navigation. `/dashboard` is real from S2 (the placeholder page, replaced by
 * the tenant dashboard in S3). `/feedback` is the cross-project feedback surface
 * that lands in S5 — marked `soon` until then. Project detail (`/projects/[id]`,
 * S4) is reached from the dashboard's project list, not the rail.
 */
export const APP_NAV: AppNavItem[] = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Feedback", href: "/feedback", soon: true },
];

export const APP_SHELL = {
  /** Accessible name for the rail's <nav> landmark. */
  navLabel: "Primary",
  /** Prefix before the tenant name in the topbar identity. */
  workspaceLabel: "Workspace",
  soonTag: "Soon",
  logoutLabel: "Sign out",
  logoutPendingLabel: "Signing out…",
  /** Fallback when a user somehow has no tenant (signup always provisions one). */
  noTenant: "—",
} as const;

/**
 * The S2 dashboard placeholder — its only job is to PROVE the auth round-trip
 * (sealed cookie → server guard → bearer-injected `GET /auth/me`). S3 replaces
 * this page with the real tenant dashboard.
 */
export const DASHBOARD_PLACEHOLDER = {
  title: "Dashboard",
  lead: "Dashboard",
  signedInPrefix: "Signed in as",
  note: "Authentication is live: this page is server-guarded, and the identity above came from vocky's /auth/me — fetched server-to-server with the bearer token unsealed from your httpOnly session cookie.",
  nextUp:
    "Projects, tenant usage, credentials, and cross-project feedback search land in the next slices.",
} as const;
