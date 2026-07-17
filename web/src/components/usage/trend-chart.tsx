import type { VockyDailyMetricCount } from "@/lib/vocky/types";

/**
 * TrendChart — the daily capture-volume series as a token-styled, dependency-free
 * inline-SVG **area chart** (restyled from the P4 bar chart in P9.S3 per
 * build-prompt §4.14). No charting library on purpose: a filled area + line drawn
 * from a handful of path strings stays small, dependency-free, and swappable.
 *
 * Presentational and props-only. Generic over `VockyDailyMetricCount[]`, which is
 * the SAME series shape for the tenant aggregate (`GET /app/usage`, P4.S3) and
 * one project's drill-down (`GET /app/projects/{id}/usage`, P4.S4) — S4 reuses
 * this as-is.
 *
 * Two shapes it must survive (both real, both hit in the live E2E):
 *   - `days: []` — a tenant with ZERO projects gets NO series at all, because
 *     vocky short-circuits to `_zeroed_metrics()` rather than zero-filling. This
 *     renders the empty note box; it never touches the SVG scale.
 *   - every bucket `0` — a tenant WITH projects but no captures gets a fully
 *     zero-filled series. `max` is floored at 1 so the scale never divides by
 *     zero, and every point lands on the baseline — the area collapses to a flat
 *     line along the bottom.
 *
 * Rendering: `preserveAspectRatio="none"` lets the area stretch fluidly to any
 * width; the line keeps `vector-effect="non-scaling-stroke"` so its weight stays
 * crisp under that stretch. The green fill fades top→bottom via a `<linearGradient>`
 * and a hairline baseline anchors the series; the two axis labels are HTML below.
 *
 * A11y: the SVG is `role="img"` with an `aria-label`, and the full series is also
 * summarized in an `sr-only` sentence — a screen reader gets the peak and the
 * total rather than an unlabeled path. Each point carries a `<title>` for a native
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

/** viewBox height (width is a fixed 100 so `x` reads as a percentage). */
const H = 42;
/** Inner padding (viewBox units) top and bottom, so peaks/baselines never clip. */
const PAD = 2;
/** Gradient id — one chart per page in practice; the fill is identical anyway. */
const GRADIENT_ID = "trend-area-gradient";

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

  const n = days.length;
  // Floored at 1: an all-zero (fully zero-filled) series must not divide by zero.
  const max = Math.max(1, ...days.map((d) => d.total));
  const grandTotal = days.reduce((sum, d) => sum + d.total, 0);
  const peak = days.reduce<VockyDailyMetricCount | null>(
    (best, d) => (best === null || d.total > best.total ? d : best),
    null,
  );

  // A single day pins to the horizontal center; otherwise points fan across the
  // full 0–100 width. `y` inverts total→height inside the padded band.
  const points = days.map((d, i) => ({
    x: n > 1 ? (i / (n - 1)) * 100 : 50,
    y: H - (d.total / max) * (H - 2 * PAD) - PAD,
    day: d.day,
    total: d.total,
  }));

  const line = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");
  const area = `${line} L 100 ${H - PAD} L 0 ${H - PAD} Z`;

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
            viewBox={`0 0 100 ${H}`}
            preserveAspectRatio="none"
            className="h-40 w-full"
          >
            <defs>
              <linearGradient id={GRADIENT_ID} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0"
                  stopColor="var(--color-green)"
                  stopOpacity={0.22}
                />
                <stop
                  offset="1"
                  stopColor="var(--color-green)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

            <line
              x1="0"
              y1={H - PAD}
              x2="100"
              y2={H - PAD}
              stroke="var(--color-hairline)"
              strokeWidth={0.6}
            />

            <path d={area} fill={`url(#${GRADIENT_ID})`} />
            <path
              d={line}
              fill="none"
              stroke="var(--color-green)"
              strokeWidth={1.4}
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />

            {points.map((p) => (
              <circle
                key={p.day}
                cx={p.x}
                cy={p.y}
                r={0.9}
                fill="var(--color-green)"
              >
                <title>{`${dayLabel(p.day)}: ${p.total.toLocaleString("en-US")}`}</title>
              </circle>
            ))}
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
