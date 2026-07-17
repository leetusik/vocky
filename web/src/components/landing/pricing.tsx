import Link from "next/link";

import { Badge, Button, buttonVariants, Card, Section } from "@/components/ui";
import { LANDING } from "@/content";
import { cn } from "@/lib/utils";

// Pricing (P9.S6, build-prompt §7.3 / §9). Resolves the design's Free-now +
// paid-later question: a featured **Free** card (available today) beside a muted
// **Pro & Teams — coming later** card. The "coming later" control is COPY ONLY —
// a disabled Button, NOT a waitlist form (no backend this round, §9). Anchored
// `#pricing`; `<Section reveal>` for the one-shot reveal.

const { pricing } = LANDING;

// A green check preceding each included / listed item.
function Check({ muted }: { muted?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={muted ? "mt-0.5 text-muted" : "mt-0.5 text-green"}
    >
      ✓
    </span>
  );
}

export function Pricing() {
  return (
    <Section id="pricing" tone="default" reveal>
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-heading-2 text-ink">{pricing.heading}</h2>
        <p className="mt-3 text-body-md text-steel">{pricing.sub}</p>
      </div>

      <div className="mx-auto mt-10 grid max-w-4xl gap-6 md:grid-cols-2">
        {/* Free — available now, featured. */}
        <Card variant="pricingFeatured">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-heading-4 text-ink">{pricing.free.name}</h3>
            <Badge variant="accent">{pricing.free.badge}</Badge>
          </div>

          <p className="mt-4 flex items-baseline gap-2">
            <span className="text-heading-1 text-ink">
              {pricing.free.price}
            </span>
            <span className="text-body-sm text-steel">
              {pricing.free.priceNote}
            </span>
          </p>

          <ul className="mt-6 space-y-2.5 text-body-sm text-slate">
            {pricing.free.inclusions.map((item) => (
              <li key={item} className="flex gap-2.5">
                <Check />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <Link
            href={pricing.free.cta.href}
            className={cn(
              buttonVariants({ variant: "primary" }),
              "mt-7 w-full",
            )}
          >
            {pricing.free.cta.label}
          </Link>
        </Card>

        {/* Pro & Teams — coming later, muted. Disabled control, no waitlist. */}
        <Card variant="pricing" className="border-hairline-soft bg-surface">
          <h3 className="text-heading-4 text-steel">{pricing.pro.name}</h3>

          <p className="mt-4 text-heading-1 text-muted">{pricing.pro.price}</p>

          <ul className="mt-6 space-y-2.5 text-body-sm text-steel">
            {pricing.pro.items.map((item) => (
              <li key={item} className="flex gap-2.5">
                <Check muted />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <Button variant="secondary" disabled className="mt-7 w-full">
            {pricing.pro.disabledLabel}
          </Button>
        </Card>
      </div>
    </Section>
  );
}
