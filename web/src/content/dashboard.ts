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

/**
 * Status-keyed org-credential error copy (P10.S4) — shared by both the mint
 * and revoke actions on the dashboard's org-keys panel, mirroring the
 * `MINT_CREDENTIAL_ERRORS` / `REVOKE_CREDENTIAL_ERRORS` split in `project.ts`
 * but consolidated into one object since both actions live on this single
 * panel. Errors map by HTTP STATUS only, never by vocky's `detail` text; any
 * status not covered here falls through to `generic`.
 */
export const ORG_CREDENTIAL_ERRORS = {
  /** Client-side zod rejection, or vocky's own 400 on mint (name >200 chars). */
  invalidName: "Key names must be 200 characters or fewer.",
  /** A tampered/garbled hidden input on revoke — the id is not a user-facing field. */
  invalidRequest: "Could not revoke that key. Reload the page and try again.",
  /** 401 — the session died mid-request; the next navigation bounces to /login. */
  sessionExpired: "Your session has expired. Sign in again to continue.",
  /** 404 on revoke — the key is gone, was never an org key, or is another org's. */
  notFound: "That key no longer exists.",
  /** 5xx / network / anything else, for either action. */
  generic: "Something went wrong. Please try again.",
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
    /**
     * `daily_counts: []` — a tenant with no projects gets no series at all.
     * Near-unreachable as of P10 (signup provisions a `"default"` project for
     * every new account, so "zero projects" no longer happens by default) —
     * kept as a defensive fallback, since an empty series is still
     * representable and nothing guarantees a tenant keeps at least one project
     * forever.
     */
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
     * would otherwise bypass copy-as-data. Near-unreachable as of P10 (signup
     * provisions a `"default"` project for every new account) — kept as a
     * defensive fallback: an empty project list is still representable.
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

  /**
   * Org-keys panel copy (P10.S4) — a fourth section on `/dashboard`, alongside
   * usage/trend/projects. An org-level key (`project_id: null`) authorizes
   * capture, read, and manage across every project in the org; capture under
   * one can name the project to route into (get-or-created, defaulting to
   * `"default"`). Deliberately disjoint from the per-project drill-down: an
   * org key never appears in a project's own credentials list, which is why
   * this panel exists.
   */
  orgKeys: {
    heading: "Organization keys",
    lead: 'An organization key works across every project in your org — capture can name the project to route into, defaulting to "default".',
    columns: {
      name: "Name",
      key: "Key",
      created: "Created",
      lastUsed: "Last used",
      status: "Status",
      /** Header for the trailing actions column (visually empty, sr-only text). */
      actions: "Actions",
    },
    /** Overrides `DataTable`'s built-in default, which bypasses copy-as-data. */
    empty:
      "No organization keys yet. Create one below to start sending feedback across projects.",
    /** `name === null` — the key was minted without a label. */
    unnamed: "Unnamed key",
    /** `last_used_at === null` — the key has never been used to ingest. */
    never: "Never",
    /** vocky has no `status` field: Active ⇔ `revoked_at === null`. */
    statusActive: "Active",
    statusRevoked: "Revoked",

    mint: {
      heading: "New organization key",
      nameLabel: "Key name",
      /** Optional: vocky defaults an omitted/blank name to `null`. */
      nameHint: "Optional — a label to tell your keys apart.",
      namePlaceholder: "e.g. Mobile app",
      submitLabel: "Create key",
      submitPendingLabel: "Creating…",
    },

    /**
     * The show-once panel, rendered via the shared `<ShowOnceKey>` component
     * (lifted out of the project mint form in this same slice). vocky returns
     * the plaintext `vk_` key EXACTLY ONCE and stores only its hash — there is
     * no "reveal again".
     */
    keyPanel: {
      heading: "Copy your new key now",
      warning:
        "This is the only time this key will ever be shown. It cannot be recovered — if you lose it, revoke it and create a new one.",
      /** Accessible name for the key value itself. */
      keyLabel: "New organization API key",
      copyLabel: "Copy",
      copiedLabel: "Copied",
      copyFailedLabel: "Copy failed — select the key and copy it manually.",
      dismissLabel: "Dismiss",
    },

    revoke: {
      label: "Revoke",
      /** Shown in place of the button once the confirm step is armed. */
      confirmPrompt: "Revoke?",
      confirmLabel: "Yes, revoke",
      cancelLabel: "Cancel",
      pendingLabel: "Revoking…",
      /** Accessible name for the per-row action (the label alone is ambiguous). */
      ariaLabelPrefix: "Revoke key",
    },
  },
} as const;
