import Link from "next/link";

import { buttonVariants } from "@/components/ui";
import { STATES } from "@/content";
import { cn } from "@/lib/utils";

// Root not-found (build-prompt §6). Catches any unmatched URL outside the `(app)`
// group and any `notFound()` that bubbles past it; renders on the bare canvas body
// (the root layout), so it centers itself full-page.
//
// LOCKED FLOOR — 404-never-403: the subcopy never confirms whether a resource
// exists ("…or isn't yours to see"), so a missing page and a forbidden one are
// indistinguishable. The copy is verbatim from `@/content` STATES.notFound.
export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <p className="font-mono text-[64px] leading-none font-bold text-green-dark tabular-nums">
        {STATES.notFound.code}
      </p>
      <h1 className="mt-6 text-heading-4 text-ink">{STATES.notFound.title}</h1>
      <p className="mt-2 text-body-sm text-steel">{STATES.notFound.body}</p>
      <Link
        href="/dashboard"
        className={cn(buttonVariants({ variant: "secondary" }), "mt-6")}
      >
        {STATES.notFound.back}
      </Link>
    </main>
  );
}
