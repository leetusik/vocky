// Tenant-dashboard copy (P4.S3) — the post-login home: usage totals, the daily
// capture trend, the projects list, and create-project. Copy-as-data per the S1
// convention: the page never hardcodes strings inline.
//
// As in `auth.ts`, the form's error copy is keyed by HTTP STATUS, never by
// vocky's `detail` text — the text is a server-side implementation detail that
// may change wording at any time, and mapping it into UI copy would couple the
// two.

export interface StatTileCopy {
  /** Which `VockyMetricCounts` field this tile reads. */
  key: "total" | "liked" | "disliked" | "unrated";
  label: string;
}

/** Status-keyed create-project error copy. */
export const CREATE_PROJECT_ERRORS = {
  /** Client-side zod rejection, or vocky's own 400 (blank / >200 chars). */
  invalidName: "Enter a project name of 1–200 characters.",
  /** 401 — the session died mid-request; the next navigation bounces to /login. */
  sessionExpired: "Your session has expired. Sign in again to continue.",
  /** 5xx / network / anything else. */
  generic: "Could not create the project. Please try again.",
} as const;

export const DASHBOARD = {
  /** Document <title> (the SITE template appends " · vocky"). */
  title: "Dashboard",
  lead: "Dashboard",

  usage: {
    heading: "Capture volume",
    /** Rendered as `{prefix} {range}` beside the heading. */
    windowPrefix: "Last 30 days ·",
    /** Shown when the window bounds cannot be parsed (defensive). */
    windowUnknown: "Last 30 days",
    tiles: [
      { key: "total", label: "Total" },
      { key: "liked", label: "Liked" },
      { key: "disliked", label: "Disliked" },
      { key: "unrated", label: "Unrated" },
    ] as StatTileCopy[],
  },

  trend: {
    heading: "Daily trend",
    /**
     * The window's edge buckets are partial days (vocky's default window starts
     * at a mid-day instant `now − 30d`), so the first/last bars are not
     * comparable to a full day. Said once, under the chart.
     */
    partialDayNote: "First and last days are partial.",
    /** `daily_counts: []` — a tenant with no projects gets no series at all. */
    empty: "No capture activity in this window yet.",
    /** Screen-reader summary prefix for the chart: `{prefix} {n} days…`. */
    ariaLabel: "Daily feedback capture volume",
  },

  projects: {
    heading: "Projects",
    columns: {
      name: "Name",
      created: "Created",
    },
    /**
     * Overrides `DataTable`'s built-in default ("No items to display."), which
     * would otherwise bypass copy-as-data.
     */
    empty: "No projects yet. Create your first one below.",
  },

  createProject: {
    heading: "New project",
    nameLabel: "Project name",
    namePlaceholder: "e.g. Support widget",
    submitLabel: "Create project",
    submitPendingLabel: "Creating…",
  },
} as const;
