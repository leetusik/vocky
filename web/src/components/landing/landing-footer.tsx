import Link from "next/link";

import { Mark, Wordmark } from "@/components/brand";
import { Section } from "@/components/ui";
import { LANDING } from "@/content";

// Landing footer (P9.S6, build-prompt §7.3). A dark forest band carrying the
// brand lockup + tagline and three link columns (Product / Project / Account),
// closing on the legal line. The `Project` column's Documentation / GitHub / MIT
// license all point at the real repo (external), never a fake `/docs` route.
//
// Rendered as a real `<footer>` landmark wrapping a `Section` (which cannot emit
// `<footer>` itself) so the tonal band + max-w-page container are reused while the
// landmark semantics stay correct.

const { footer } = LANDING;

function FooterLink({
  href,
  external,
  children,
}: {
  href: string;
  external?: boolean;
  children: React.ReactNode;
}) {
  const className =
    "text-body-sm text-on-dark-muted transition-colors hover:text-on-dark";
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
      >
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

export function LandingFooter() {
  return (
    <footer>
      <Section as="div" tone="forest" className="py-section">
        <div className="grid gap-10 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
          {/* Brand + tagline. */}
          <div>
            <div className="flex items-center gap-2.5">
              <Mark size={32} />
              <Wordmark tone="dark" />
            </div>
            <p className="mt-4 max-w-xs text-body-sm text-on-dark-muted">
              {footer.tagline}
            </p>
          </div>

          {/* Link columns. */}
          {footer.columns.map((column) => (
            <nav key={column.heading} aria-label={column.heading}>
              <h2 className="text-micro text-trust-sage uppercase">
                {column.heading}
              </h2>
              <ul className="mt-4 space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <FooterLink
                      href={link.href}
                      external={"external" in link ? link.external : undefined}
                    >
                      {link.label}
                    </FooterLink>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 border-t border-hairline-dark pt-6">
          <p className="text-caption text-on-dark-muted">{footer.legal}</p>
        </div>
      </Section>
    </footer>
  );
}
