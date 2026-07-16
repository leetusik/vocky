// Project-detail copy (P4.S4) — the per-project drill-down: this project's usage,
// its ingest credentials, and the mint/revoke flows. Copy-as-data per the S1
// convention: the page never hardcodes strings inline.
//
// As in `auth.ts` / `dashboard.ts`, form error copy is keyed by HTTP STATUS, never
// by vocky's `detail` text — the text is a server-side implementation detail.

import type { StatTileCopy } from "./dashboard";

/** Status-keyed mint-credential error copy. */
export const MINT_CREDENTIAL_ERRORS = {
  /** Client-side zod rejection, or vocky's own 400 (name >200 chars). */
  invalidName: "Key names must be 200 characters or fewer.",
  /** 401 — the session died mid-request; the next navigation bounces to /login. */
  sessionExpired: "Your session has expired. Sign in again to continue.",
  /** 404 — the project vanished (or was never ours) between render and submit. */
  notFound: "This project no longer exists.",
  /** 5xx / network / anything else. */
  generic: "Could not create the key. Please try again.",
} as const;

/** Status-keyed revoke-credential error copy. */
export const REVOKE_CREDENTIAL_ERRORS = {
  /** A tampered/garbled hidden input — the ids are not user-facing fields. */
  invalidRequest: "Could not revoke that key. Reload the page and try again.",
  sessionExpired: "Your session has expired. Sign in again to continue.",
  /** 404 — the key or project is gone (or is another tenant's). */
  notFound: "That key no longer exists.",
  generic: "Could not revoke the key. Please try again.",
} as const;

export const PROJECT = {
  /**
   * Document <title> (the SITE template appends " · vocky"). STATIC, not the
   * project's name: the vocky client is `cache: "no-store"`, so a
   * `generateMetadata` title would cost a second uncached round-trip for a
   * cosmetic gain.
   */
  title: "Project",

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
    partialDayNote: "First and last days are partial.",
    /**
     * DEFENSIVE ONLY — required by `TrendChart`'s props, but unreachable on this
     * endpoint: `_project_usage_response` has no zero-project short-circuit, so
     * a capture-less project still gets a fully zero-filled series rather than
     * `daily_counts: []`. (Contrast the dashboard, where it is a real state.)
     */
    empty: "No capture activity in this window yet.",
    ariaLabel: "Daily feedback capture volume",
  },

  credentials: {
    heading: "API keys",
    /** Explains what the keys are for, once, above the table. */
    lead: "Use a key's value as the API credential your service sends to vocky.",
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
    empty: "No keys yet. Create one below to start sending feedback.",
    /** `name === null` — the key was minted without a label. */
    unnamed: "Unnamed key",
    /** `last_used_at === null` — the key has never been used to ingest. */
    never: "Never",
    /** vocky has no `status` field: Active ⇔ `revoked_at === null`. */
    statusActive: "Active",
    statusRevoked: "Revoked",
  },

  mint: {
    heading: "New API key",
    nameLabel: "Key name",
    /** Optional: vocky defaults an omitted/blank name to `null`. */
    nameHint: "Optional — a label to tell your keys apart.",
    namePlaceholder: "e.g. Production widget",
    submitLabel: "Create key",
    submitPendingLabel: "Creating…",
  },

  /**
   * The show-once panel. vocky returns the plaintext `vk_` key EXACTLY ONCE and
   * stores only its hash — there is no "reveal again". The copy has to carry that
   * weight, because a dismissed panel is a lost key.
   */
  keyPanel: {
    heading: "Copy your new key now",
    warning:
      "This is the only time this key will ever be shown. It cannot be recovered — if you lose it, revoke it and create a new one.",
    /** Accessible name for the key value itself. */
    keyLabel: "New API key",
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
} as const;
