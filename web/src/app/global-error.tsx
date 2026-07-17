"use client";

import { Mark } from "@/components/brand";
import { Button } from "@/components/ui";
import { STATES } from "@/content";

// Global-error (build-prompt §6). The last-resort boundary that fires when the
// ROOT layout itself throws — so it REPLACES the root layout and must render its
// own `<html>` and `<body>`. It lives outside the `next/font` variable scope
// (`--font-pretendard` is set by a className on the now-crashed root `<html>`), so
// `font-sans` degrades to the Korean-capable system fallback — acceptable here per
// §6. A minimal full-page variant of the error boundary: brand mark, the fixed
// heading, and a reset. `error.message` is never surfaced (security floor).
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-canvas px-6 text-center font-sans text-ink antialiased">
        <Mark size={52} />
        <h1 className="text-heading-4 text-ink">{STATES.globalError.title}</h1>
        <Button size="sm" onClick={reset}>
          {STATES.globalError.retry}
        </Button>
      </body>
    </html>
  );
}
