import Link from "next/link";

import { Card } from "@/components/ui";
import { SITE } from "@/content";
import type { AuthPageCopy } from "@/content";

/**
 * Shared presentation for the login + signup pages (P4.S2): brand, the card with
 * lead/sub + the form island, and the cross-link to the other auth page. Server
 * component — only the `children` form is a client island.
 *
 * Light surface on the placeholder palette (unlike hi2vi's dark "secure gate",
 * whose forest/mint tokens have no vocky equivalent). The real design lands at the
 * P6 gate; this is token-only so that swap is values, not markup.
 */
export function AuthCard({
  copy,
  children,
}: {
  copy: AuthPageCopy;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-[420px]">
      <p className="mb-6 text-center text-heading-4 text-ink">{SITE.name}</p>

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
