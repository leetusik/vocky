import Link from "next/link";

import { Mark, Wordmark } from "@/components/brand";
import { buttonVariants } from "@/components/ui";
import { LANDING } from "@/content";

// Landing top nav (P9.S6, build-prompt §7.3). A sticky, translucent header on the
// light canvas — the landing's own chrome (it is OUTSIDE the `(app)` group, so no
// app shell). Server component: the in-page anchor links (Features / How it works
// / Pricing) scroll to the `<Section id>` bands, "Docs" is an external repo link,
// and the Sign in / Start free CTAs route into the auth surface.
//
// The mid nav links collapse on mobile (they are duplicated in the footer); the
// brand and the two CTAs stay visible at every width.

const { nav } = LANDING;

export function LandingNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-hairline bg-canvas/85 backdrop-blur">
      <nav className="mx-auto flex max-w-page items-center gap-6 px-5 py-3 md:px-14">
        <Link
          href="/"
          className="flex items-center gap-2.5"
          aria-label="vocky home"
        >
          <Mark size={32} />
          <Wordmark />
        </Link>

        <ul className="ml-4 hidden items-center gap-7 md:flex">
          {nav.links.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                {...("external" in link && link.external
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
                className="text-body-sm text-steel transition-colors hover:text-ink"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href={nav.signIn.href}
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            {nav.signIn.label}
          </Link>
          <Link
            href={nav.startFree.href}
            className={buttonVariants({ variant: "primary", size: "sm" })}
          >
            {nav.startFree.label}
          </Link>
        </div>
      </nav>
    </header>
  );
}
