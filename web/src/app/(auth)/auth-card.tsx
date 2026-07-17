import Link from "next/link";

import { Mark, Wordmark } from "@/components/brand";
import { Card } from "@/components/ui";
import type { AuthPageCopy } from "@/content";

/**
 * Shared presentation for the login + signup pages (P4.S2; restyled to the vocky
 * system in P9.S4): the brand lockup (mark + wordmark), the `feature` card with
 * lead/sub + the form island, and the cross-link to the other auth page. Server
 * component — only the `children` form is a client island.
 *
 * A brand moment on a light surface: the larger 52px Mark + the Wordmark sit
 * centered above the card. The identical-401-error mapping stays in the form/BFF
 * (a locked floor) — untouched here.
 */
export function AuthCard({
  copy,
  children,
}: {
  copy: AuthPageCopy;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-[400px]">
      <div className="mb-6 flex items-center justify-center gap-3">
        <Mark size={52} />
        <Wordmark className="text-[28px]" />
      </div>

      <Card variant="feature">
        <h1 className="text-heading-3 text-ink">{copy.lead}</h1>
        <p className="mt-2 text-body-sm text-steel">{copy.sub}</p>
        <div className="mt-6">{children}</div>
      </Card>

      <p className="mt-6 text-center text-body-sm text-steel">
        {copy.altPrompt}{" "}
        <Link
          href={copy.altHref}
          className="font-medium text-green-dark hover:underline"
        >
          {copy.altLinkLabel}
        </Link>
      </p>
    </div>
  );
}
