import Link from "next/link";

import { buttonVariants, Section } from "@/components/ui";
import { LANDING } from "@/content";

// Closing CTA (P9.S6, build-prompt §7.3). A dark forest band that repeats the
// core ask before the footer. The green primary CTA pops on the forest ground;
// "Read the docs" uses the `dark` Button variant (transparent, light border) for
// the on-dark surface. `<Section reveal>` for the one-shot reveal.

const { closing } = LANDING;

export function ClosingCTA() {
  return (
    <Section tone="forest" reveal>
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-heading-2 text-on-dark">{closing.heading}</h2>
        <p className="mt-4 text-body-lg text-on-dark-muted">{closing.sub}</p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href={closing.ctaPrimary.href}
            className={buttonVariants({ variant: "primary", size: "lg" })}
          >
            {closing.ctaPrimary.label}
          </Link>
          <a
            href={closing.ctaSecondary.href}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonVariants({ variant: "dark", size: "lg" })}
          >
            {closing.ctaSecondary.label}
          </a>
        </div>
      </div>
    </Section>
  );
}
