import { Card, Grid } from "@/components/ui";
import type { StatTileCopy } from "@/content";
import type { VockyMetricCounts, VockyUsageWindow } from "@/lib/vocky/types";
import { cn } from "@/lib/utils";

/**
 * StatTiles — the four capture-volume totals (total / liked / disliked /
 * unrated) as a row of stat cards, plus the window label.
 *
 * Presentational and props-only: it takes the `totals` + `window` straight off a
 * usage payload and never fetches. Generic over `VockyMetricCounts`, which is the
 * SAME shape for the tenant aggregate (`GET /app/usage`, P4.S3) and one project's
 * drill-down (`GET /app/projects/{id}/usage`, P4.S4) — S4 reuses this component
 * as-is, passing its own totals.
 *
 * Which tiles render (and their labels) is driven by the `tiles` prop from
 * `@/content`, so copy stays data.
 */
export interface StatTilesProps {
  heading: string;
  totals: VockyMetricCounts;
  tiles: readonly StatTileCopy[];
  /** vocky's echoed window; the label is derived from it, never recomputed. */
  window: VockyUsageWindow;
  windowPrefix: string;
  /** Fallback label when a bound is unparseable. */
  windowUnknown: string;
}

/**
 * Leading rating dot per tile (build-prompt §4.13): the total tile carries none;
 * the three rating tiles get a small colored dot echoing the rating palette
 * (liked = green, disliked = danger, unrated = muted). `null` = no dot.
 */
const TILE_DOT: Record<StatTileCopy["key"], string | null> = {
  total: null,
  liked: "bg-green",
  disliked: "bg-danger",
  unrated: "bg-muted",
};

/** `"2026-06-16T…" → "Jun 16"`, or `null` when the bound will not parse. */
function shortDate(iso: string): string | null {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return null;
  return at.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** `"Jun 16 – Jul 16"` from the echoed window, or the fallback. */
function windowLabel(
  window: VockyUsageWindow,
  prefix: string,
  fallback: string,
): string {
  const start = shortDate(window.start_ingested_at);
  const end = shortDate(window.end_ingested_at);
  if (!start || !end) return fallback;
  return `${prefix} ${start} – ${end}`;
}

export function StatTiles({
  heading,
  totals,
  tiles,
  window,
  windowPrefix,
  windowUnknown,
}: StatTilesProps) {
  return (
    <section aria-labelledby="usage-totals">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="usage-totals" className="text-heading-4 text-ink">
          {heading}
        </h2>
        <p className="text-body-sm text-steel">
          {windowLabel(window, windowPrefix, windowUnknown)}
        </p>
      </div>

      <Grid cols={4} className="mt-4">
        {tiles.map((tile) => (
          <Card key={tile.key} variant="base" className="p-4">
            <p className="flex items-center gap-1.5 text-caption font-medium text-steel">
              {TILE_DOT[tile.key] ? (
                <span
                  aria-hidden="true"
                  className={cn(
                    "inline-block size-1.5 rounded-full",
                    TILE_DOT[tile.key],
                  )}
                />
              ) : null}
              {tile.label}
            </p>
            <p className="mt-1 font-mono text-heading-3 text-ink tabular-nums">
              {totals[tile.key].toLocaleString("en-US")}
            </p>
          </Card>
        ))}
      </Grid>
    </section>
  );
}
