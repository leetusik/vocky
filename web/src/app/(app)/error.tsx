"use client";

import { Mark } from "@/components/brand";
import { Button, Card } from "@/components/ui";
import { STATES } from "@/content";

// Error boundary for the `(app)` route group (build-prompt §6). A Next.js error
// boundary is always a client component and receives `{ error, reset }`; it
// renders INSIDE the app shell (the boundary sits within `(app)/layout.tsx`), so
// a failed data fetch surfaces as a real vocky state, not Next's default overlay.
//
// SECURITY FLOOR: never render `error.message`. A thrown server error can carry
// internal detail (a stack, an upstream body), so the copy is fixed and the raw
// message is dropped. `reset()` re-attempts the failed render.
//
// The mark is the S3 brand asset restyled to the danger tint via its
// `tileClassName` prop — not a fork of the geometry.
export default function AppError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-page items-center justify-center">
      <Card
        variant="feature"
        role="alert"
        className="flex max-w-md flex-col items-center gap-4 text-center"
      >
        <Mark size={52} tileClassName="fill-danger" />
        <div className="space-y-2">
          <h1 className="text-heading-4 text-ink">{STATES.error.title}</h1>
          <p className="text-body-sm text-steel">{STATES.error.body}</p>
        </div>
        <Button size="sm" onClick={reset}>
          {STATES.error.retry}
        </Button>
      </Card>
    </div>
  );
}
