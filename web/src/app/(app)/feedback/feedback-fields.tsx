import { Badge } from "@/components/ui";
import { FEEDBACK } from "@/content";

// P4.S5 — the two renderings the feedback LIST and its DETAIL page must agree
// on. Deliberately NOT a `@/components/ui` primitive: both encode vocky's own
// shapes (`feedback_value`'s 1|2|null, UTC ISO timestamps), while the ui/ kit is
// domain-free and P6-swappable. Colocated in the route folder — the S4 idiom for
// a non-route file a page needs (only page/route/layout files become routes).

/**
 * `"2026-07-16T09:31:02Z"` → `"Jul 16, 2026, 09:31"`; unparseable → as-is.
 *
 * Pinned to UTC, and labeled as such wherever it renders. vocky serializes every
 * timestamp as UTC, and these render on the SERVER — so leaving the zone unpinned
 * would silently print the container's clock (whatever the deploy box is set to)
 * and pass it off as the reader's local time. Unlike S3/S4's date-only
 * formatters, this keeps the time: feedback is ordered by the minute, and a
 * date-only stamp would make a newest-first page look unsorted.
 */
export function formatUtc(iso: string): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  return at.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

/** A UTC timestamp with the machine-readable ISO kept in `dateTime`. */
export function Timestamp({ iso }: { iso: string }) {
  return (
    <time
      dateTime={iso}
      className="font-mono text-body-sm text-steel tabular-nums"
    >
      {formatUtc(iso)}
    </time>
  );
}

/**
 * vocky's explicit-action rating: `1` = like, `2` = dislike, `null` = unrated.
 *
 * `null` is the COMMON case, not an error — plenty of captures carry only text —
 * so it renders as muted text rather than a badge: an absent signal is not a
 * signal. Both variants come from the existing placeholder palette (S5 adds no
 * badge token), so the P6 design gate swaps values only.
 */
export function RatingBadge({ value }: { value: 1 | 2 | null }) {
  if (value === 1) {
    return <Badge variant="softGreen">{FEEDBACK.list.valueLiked}</Badge>;
  }
  if (value === 2) {
    return <Badge variant="archive">{FEEDBACK.list.valueDisliked}</Badge>;
  }
  return (
    <span className="text-body-sm text-steel">{FEEDBACK.list.valueUnrated}</span>
  );
}
