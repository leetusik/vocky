import { Section } from "@/components/ui";
import { LANDING } from "@/content";

// Trust strip (P9.S6, build-prompt §7.3). A thin band directly under the hero —
// real product facts, not fake customer logos. The Section's generous default
// vertical rhythm is trimmed here (the strip is a one-line band, not a full
// section). `break-keep` protects the inline Korean ("결제"). No Reveal — it sits
// just below the fold and reads as part of the hero.

const { trust } = LANDING;

export function TrustStrip() {
  return (
    <Section tone="surfaceSoft" className="py-6 md:py-8">
      <ul className="flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-body-sm break-keep text-steel">
        {trust.items.map((item, i) => (
          <li key={item} className="flex items-center gap-x-3">
            {i > 0 && (
              <span aria-hidden="true" className="text-hairline-strong">
                ·
              </span>
            )}
            <span className={i === 0 ? "font-mono text-green-dark" : undefined}>
              {item}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}
