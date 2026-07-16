import type { VockyDailyMetricCount } from "@/lib/vocky/types";

/**
 * TrendChart — the daily capture-volume series as a token-styled inline-SVG bar
 * chart. No charting dependency on purpose: the design gate is deferred to P6
 * (D-P4-3), so this stays ~small, dependency-free, and swappable.
 *
 * Presentational and props-only. Generic over `VockyDailyMetricCount[]`, which is
 * the SAME series shape for the tenant aggregate (`GET /app/usage`, P4.S3) and
 * one project's drill-down (`GET /app/projects/{id}/usage`, P4.S4) — S4 reuses
 * this as-is.
 *
 * Two shapes it must survive (both real, both hit in the live E2E):
 *   - `days: []` — a tenant with ZERO projects gets NO series at all, because
 *     vocky short-circuits to `_zeroed_metrics()` rather than zero-filling. This
 *     renders the empty state; it must never divide by a zero bucket count.
 *   - every bucket `0` — a tenant WITH projects but no captures gets a fully
 *     zero-filled series. `maxTotal` is floored at 1 so the scale never divides
 *     by zero, and every bar renders as a flat baseline stub.
 *
 * Rendering: `preserveAspectRatio="none"` lets the bars stretch fluidly to any
 * width while staying crisp rectangles (the standard axis-aligned-bar trick).
 * Nothing inside the SVG is stroked or text — distortion-free by construction;
 * the axis labels are HTML underneath.
 *
 * A11y: the SVG is `role="img"` with an `aria-label`, and the full series is also
 * summarized in an `sr-only` sentence — a screen reader gets the peak and the
 * total rather than 31 unlabeled rects. Each bar carries a `<title>` for a native
 * hover tooltip.
 */
export interface TrendChartProps {
  heading: string;
  days: VockyDailyMetricCount[];
  /** Shown instead of the chart when `days` is empty. */
  empty: string;
  /** Note that the window's edge buckets are partial days. */
  partialDayNote: string;
  /** Accessible name for the chart. */
  ariaLabel: string;
}

/** Bar slot width in viewBox units (bar + gutter). */
const SLOT = 10;
/** Bar width within its slot; the remainder is the gutter. */
const BAR = 7;
/** viewBox height. */
const H = 100;

/** `"2026-06-16"` → `"Jun 16"`. Parsed as UTC — the value is date-only, so
 * letting the runtime apply a local offset would shift the label by a day in any
 * negative-offset timezone. */
function dayLabel(day: string): string {
  const at = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(at.getTime())) return day;
  return at.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function TrendChart({
  heading,
  days,
  empty,
  partialDayNote,
  ariaLabel,
}: TrendChartProps) {
  const hasSeries = days.length > 0;

  // Floored at 1: an all-zero (fully zero-filled) series must not divide by zero.
  const maxTotal = Math.max(1, ...days.map((d) => d.total));
  const grandTotal = days.reduce((sum, d) => sum + d.total, 0);
  const peak = days.reduce<VockyDailyMetricCount | null>(
    (best, d) => (best === null || d.total > best.total ? d : best),
    null,
  );

  const summary =
    peak === null
      ? empty
      : `${ariaLabel}: ${grandTotal.toLocaleString("en-US")} total across ${days.length} ${
          days.length === 1 ? "day" : "days"
        }, from ${dayLabel(days[0].day)} to ${dayLabel(days[days.length - 1].day)}. Peak ${peak.total.toLocaleString("en-US")} on ${dayLabel(peak.day)}.`;

  return (
    <section aria-labelledby="usage-trend">
      <h2 id="usage-trend" className="text-heading-4 text-ink">
        {heading}
      </h2>

      {!hasSeries ? (
        <div className="mt-4 rounded-lg border border-hairline bg-surface px-4 py-10 text-center text-body-sm text-steel">
          {empty}
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-hairline bg-canvas p-4">
          <p className="sr-only">{summary}</p>

          <svg
            role="img"
            aria-label={ariaLabel}
            viewBox={`0 0 ${days.length * SLOT} ${H}`}
            preserveAspectRatio="none"
            className="h-40 w-full"
          >
            {days.map((d, i) => {
              const height = (d.total / maxTotal) * H;
              // A zero day still renders a 1-unit stub, so the series reads as a
              // continuous timeline instead of a gap.
              const drawn = Math.max(height, 1);
              return (
                <rect
                  key={d.day}
                  x={i * SLOT + (SLOT - BAR) / 2}
                  y={H - drawn}
                  width={BAR}
                  height={drawn}
                  className={d.total === 0 ? "fill-hairline" : "fill-green"}
                >
                  <title>{`${dayLabel(d.day)}: ${d.total.toLocaleString("en-US")}`}</title>
                </rect>
              );
            })}
          </svg>

          <div
            aria-hidden="true"
            className="mt-2 flex justify-between text-caption text-steel"
          >
            <span>{dayLabel(days[0].day)}</span>
            <span>{dayLabel(days[days.length - 1].day)}</span>
          </div>

          <p className="mt-2 text-caption text-muted">{partialDayNote}</p>
        </div>
      )}
    </section>
  );
}
