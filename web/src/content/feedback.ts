// Cross-project feedback copy (P4.S5) — the flagship read surface: the searchable
// list of every project's feedback, and one record's detail. Copy-as-data per the
// S1 convention: the pages never hardcode strings inline.
//
// READ + SEARCH ONLY. Feedback management (edit / delete / operator comments)
// lives on the `vk_`-keyed `/api/project/feedback` surface, not this app — so
// there is deliberately no action copy here, only labels for what is displayed.

export const FEEDBACK = {
  /** Document <title> (the SITE template appends " · vocky"). */
  title: "Feedback",
  lead: "Feedback",

  filters: {
    heading: "Search & filter",
    /**
     * `q` is a case-insensitive SUBSTRING match over four concatenated fields
     * (message + comment + target text + trigger message) — not tokenized, not
     * relevance-ranked. The hint says "any part of" rather than "words" because
     * a partial word matches, which is exactly what makes Korean 조사-attached
     * forms (`결제를`) findable by the stem (`결제`).
     */
    searchLabel: "Search",
    searchPlaceholder: "e.g. 결제 or checkout",
    searchHint:
      "Matches any part of the feedback text, comment, or context — Korean and English alike.",
    projectLabel: "Project",
    /** The `project_id` filter's unset option — sent as blank, then omitted. */
    projectAll: "All projects",
    valueLabel: "Rating",
    /** The `feedback_value` filter's unset option (vocky accepts only 1 or 2). */
    valueAny: "Any rating",
    valueLiked: "Liked",
    valueDisliked: "Disliked",
    submitLabel: "Search",
    /** Resets to a bare `/feedback` — clearing the fields by hand would leave the cursor. */
    resetLabel: "Clear",
  },

  list: {
    heading: "Recent feedback",
    columns: {
      when: "When",
      project: "Project",
      message: "Feedback",
      value: "Rating",
      source: "Source",
    },
    /** vocky stores UTC; rendering in the server's zone would be a silent lie. */
    timeNote: "Times are shown in UTC, newest first.",
    /**
     * TWO empty states, distinguished on purpose: an empty list means something
     * different before you own any project (nothing can arrive yet) than it does
     * after (your filters matched nothing).
     */
    emptyNoProjects:
      "No projects yet. Create one from the dashboard, then send feedback with its API key.",
    emptyNoMatches: "No feedback matches these filters.",
    /** `project_id` is null (a legacy pre-project row) or names an unlisted project. */
    unknownProject: "—",
    /** `feedback_value === null` — no explicit like/dislike was given. */
    valueUnrated: "Unrated",
    valueLiked: "Liked",
    valueDisliked: "Disliked",
  },

  pagination: {
    /**
     * Forward-only: keyset paging yields no previous cursor, and each page is its
     * own URL, so BROWSER BACK is "previous". Rendered only when `next_cursor` is
     * present.
     */
    nextLabel: "Next page",
  },

  detail: {
    /** STATIC title, not the message: the vocky client is `no-store`, so a
     *  `generateMetadata` title would cost a second uncached round-trip. */
    title: "Feedback detail",
    backLabel: "Back to feedback",
    /** The end user's own words — the reason this record exists. */
    messageHeading: "Feedback",
    /** `comment === null` — the capture carried no elaborating comment. */
    commentHeading: "Comment",
    commentNone: "No comment.",
    detailsHeading: "Details",
    fields: {
      project: "Project",
      value: "Rating",
      sourceProduct: "Product",
      sourceIntegration: "Integration",
      channel: "Channel",
      triggerType: "Trigger",
      triggerMessage: "Trigger message",
      targetType: "Target type",
      targetRole: "Target role",
      targetText: "Target text",
      conversationId: "Conversation",
      sessionId: "Session",
      userId: "End user",
      /** Caller-reported time the feedback happened; `null` when not sent. */
      eventAt: "Happened at",
      /** When vocky stored it — always present, and the list's sort key. */
      ingestedAt: "Captured at",
      id: "Record ID",
    },
    /** Any nullable field above that vocky returned as `null`. */
    fieldEmpty: "—",
    tagsHeading: "Tags",
    /** `tags: []` — an untagged capture. */
    tagsNone: "No tags.",
    commentsHeading: "Operator comments",
    /**
     * `comments: []`. Read-only here BY DESIGN: comments are written through the
     * `vk_`-keyed `/api/project/feedback` surface, not this app.
     */
    commentsNone: "No comments on this record.",
    /** `author === null` — the comment was left unattributed. */
    commentAuthorUnknown: "Unknown author",
    /**
     * The free-form caller-supplied JSON (`trigger_metadata`, `source_metadata`,
     * `attributes`, `messages`, `used_context`). No schema vocky enforces, so it
     * is shown raw, collapsed, and only when non-empty.
     */
    rawHeading: "Raw data",
    rawNone: "No additional data.",
    raw: {
      triggerMetadata: "Trigger metadata",
      sourceMetadata: "Source metadata",
      attributes: "Attributes",
      messages: "Messages",
      usedContext: "Used context",
    },
  },

  attachments: {
    heading: "Attachments",
    /** `attachments: []`. */
    none: "No attachments.",
    /** `filename === null` — uploaded without one. */
    unnamed: "Untitled file",
    /**
     * Every attachment downloads rather than opening inline — the bytes are
     * uploader-supplied, and serving, say, their HTML from our own origin would
     * be XSS. Said once, above the list.
     */
    downloadNote: "Attachments download rather than open in the browser.",
    downloadLabel: "Download",
    /** Units for `byte_size`, ascending by factors of 1024. */
    byteUnits: ["B", "KB", "MB", "GB"],
  },
} as const;
