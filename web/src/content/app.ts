// Authenticated app-shell copy + nav (P4.S2). The shell is the chrome S3–S5 render
// inside; this is the single source for its labels and rail links.

export interface AppNavItem {
  label: string;
  href: string;
  /**
   * True when the destination route does not exist yet — rendered as a muted,
   * non-interactive rail item with a "Soon" tag instead of a link that 404s. The
   * slice that ships the route drops this flag (S5 dropped the last one, so no
   * item sets it today; the affordance stays for the surfaces P6 announces
   * before it builds them).
   */
  soon?: boolean;
}

/**
 * Rail navigation — both destinations are real routes as of S5: `/dashboard` is
 * the tenant dashboard (S3) and `/feedback` the cross-project feedback list +
 * search (S5). Project detail (`/projects/[id]`, S4) is deliberately NOT here —
 * a project is reached from the dashboard's project list, and a feedback record
 * from the feedback list; the rail carries only the two top-level surfaces.
 */
export const APP_NAV: AppNavItem[] = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Feedback", href: "/feedback" },
];

export const APP_SHELL = {
  /** Accessible name for the rail's <nav> landmark. */
  navLabel: "Primary",
  /** Prefix before the tenant name in the topbar identity. */
  orgLabel: "Org",
  soonTag: "Soon",
  logoutLabel: "Sign out",
  logoutPendingLabel: "Signing out…",
  /** Fallback when a user somehow has no tenant (signup always provisions one). */
  noTenant: "—",
} as const;
