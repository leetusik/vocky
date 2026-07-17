import { Card } from "@/components/ui";
import { STATES } from "@/content";
import { cn } from "@/lib/utils";

// Loading skeleton for the feedback list (build-prompt §6). The feedback surface
// is shaped differently from the dashboard — a filter card over a results table,
// not stat-tiles + chart — so it gets its own route-level fallback rather than the
// generic `(app)/loading.tsx` mirror. Renders inside the app shell.
//
// Same skeleton grammar as the app-wide fallback: `rounded-md bg-hairline-soft`
// blocks, a subtle `animate-pulse` the global reduced-motion layer freezes, with
// `motion-reduce:animate-none` making the static-under-reduced-motion intent
// explicit (§6).

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={cn("rounded-md bg-hairline-soft", className)} />;
}

export default function FeedbackLoading() {
  return (
    <>
      <span className="sr-only" role="status">
        {STATES.loading.label}
      </span>

      <div
        aria-hidden="true"
        className="mx-auto max-w-page animate-pulse motion-reduce:animate-none"
      >
        {/* Title block (heading-3 height). */}
        <SkeletonBlock className="h-8 w-40" />

        <div className="mt-6 space-y-6">
          {/* Filter card — heading + a row of filter controls. */}
          <Card variant="base">
            <SkeletonBlock className="h-5 w-24" />
            <div className="mt-3 flex flex-col gap-4 app:flex-row app:items-end">
              <div className="app:flex-1">
                <SkeletonBlock className="h-3.5 w-16" />
                <SkeletonBlock className="mt-1.5 h-[38px] w-full" />
              </div>
              <div className="app:w-56">
                <SkeletonBlock className="h-3.5 w-16" />
                <SkeletonBlock className="mt-1.5 h-[38px] w-full" />
              </div>
              <div className="app:w-40">
                <SkeletonBlock className="h-3.5 w-16" />
                <SkeletonBlock className="mt-1.5 h-[38px] w-full" />
              </div>
              <SkeletonBlock className="h-9 w-20" />
            </div>
          </Card>

          {/* Results — heading + a run of table-row skeletons. */}
          <section>
            <SkeletonBlock className="h-6 w-40" />
            <SkeletonBlock className="mt-1 h-3.5 w-56" />
            <div className="mt-4 space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonBlock key={i} className="h-11 w-full" />
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
