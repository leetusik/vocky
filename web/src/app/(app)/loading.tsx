import { Card, Grid } from "@/components/ui";
import { STATES } from "@/content";
import { cn } from "@/lib/utils";

// Loading skeleton for the `(app)` route group (build-prompt §6). A placeholder
// mirror of the real dashboard / project shape — a title block, a `Grid cols={4}`
// of four stat-tile skeletons, a chart-height block, and a run of table-row
// skeletons — so the layout does not jump when the data resolves. It renders as
// the Suspense fallback INSIDE the app shell (the `(app)/layout.tsx` wraps this),
// so it carries only the content, not the chrome.
//
// Skeleton blocks are `rounded-md bg-hairline-soft` at each element's height. The
// `animate-pulse` shimmer is deliberately subtle and the global reduced-motion
// layer in `globals.css` already freezes it; `motion-reduce:animate-none` makes
// that intent explicit — static under reduced motion, per §6.
//
// The feedback list has its own (differently shaped) skeleton in
// `feedback/loading.tsx`; this fallback covers the stat-tile + chart surfaces
// (dashboard, project detail).

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={cn("rounded-md bg-hairline-soft", className)} />;
}

export default function AppLoading() {
  return (
    <>
      {/* Announce the wait to assistive tech; the visual skeleton is decorative. */}
      <span className="sr-only" role="status">
        {STATES.loading.label}
      </span>

      <div
        aria-hidden="true"
        className="mx-auto max-w-page animate-pulse motion-reduce:animate-none"
      >
        {/* Title block (heading-3 height). */}
        <SkeletonBlock className="h-8 w-48" />

        <div className="mt-6 space-y-6">
          {/* Stat tiles — mirror StatTiles: a heading + a Grid cols={4} of four
              compact (p-4) tile cards. */}
          <section>
            <SkeletonBlock className="h-6 w-40" />
            <Grid cols={4} className="mt-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Card key={i} variant="base" className="p-4">
                  <SkeletonBlock className="h-3.5 w-16" />
                  <SkeletonBlock className="mt-2 h-7 w-20" />
                </Card>
              ))}
            </Grid>
          </section>

          {/* Chart — a heading + a chart-height (h-40) block inside a card. */}
          <section>
            <SkeletonBlock className="h-6 w-40" />
            <Card variant="base" className="mt-4">
              <SkeletonBlock className="h-40 w-full" />
            </Card>
          </section>

          {/* Table — a heading + five row skeletons. */}
          <section>
            <SkeletonBlock className="h-6 w-40" />
            <div className="mt-4 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <SkeletonBlock key={i} className="h-11 w-full" />
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
