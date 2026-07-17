import Link from "next/link";

import { buttonVariants } from "@/components/ui";
import { STATES } from "@/content";
import { cn } from "@/lib/utils";

// In-app not-found (build-prompt §6). The three in-app `notFound()` call sites
// (project detail, feedback list, feedback detail) resolve to THIS file rather
// than the root not-found, so a missing record renders inside the app shell
// instead of dropping the reader out of the chrome. Same content as the root
// not-found; centers within the content area, not the full viewport.
//
// LOCKED FLOOR — 404-never-403: the subcopy never confirms whether a resource
// exists, so a record outside the tenant is indistinguishable from one that never
// existed. Copy is verbatim from `@/content` STATES.notFound.
export default function AppNotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-page flex-col items-center justify-center px-6 py-12 text-center">
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
    </div>
  );
}
