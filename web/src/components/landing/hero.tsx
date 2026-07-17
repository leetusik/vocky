import Link from "next/link";

import {
  Badge,
  buttonVariants,
  Card,
  Chip,
  EndpointCard,
  Section,
} from "@/components/ui";
import { LANDING } from "@/content";
import { cn } from "@/lib/utils";

// Landing hero (P9.S6, build-prompt §7.3). Above the fold, so NO Reveal — it must
// paint immediately. Two columns on large screens: the value proposition (eyebrow
// + headline + sub + CTAs) beside the product proof — a real `POST /api/feedback`
// request panel (EndpointCard) layered over the "captured" record it produces
// (Korean message + disliked Badge + two Chip tags). Server component; the CTAs
// are anchor links styled with `buttonVariants`.
//
// The Korean message carries `break-keep` (word-break: keep-all) so an eojeol
// never splits across lines — the same locked floor globals.css applies to
// headings, made explicit here for the body-copy example.

const { hero } = LANDING;

const requestText = `${hero.request.auth}
Content-Type: application/json

${hero.request.body}`;

export function Hero() {
  return (
    <Section tone="default" className="pt-12 md:pt-16">
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        {/* Left — the pitch. */}
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-green-soft px-3 py-1 text-caption font-semibold text-green-dark">
            <span
              aria-hidden="true"
              className="size-1.5 rounded-full bg-green"
            />
            {hero.eyebrow}
          </p>

          <h1 className="mt-5 text-heading-1 text-ink sm:text-display-lg lg:text-hero-display">
            {hero.headline}
          </h1>

          <p className="mt-6 max-w-xl text-body-lg text-steel">{hero.sub}</p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={hero.ctaPrimary.href}
              className={buttonVariants({ variant: "primary", size: "lg" })}
            >
              {hero.ctaPrimary.label}
            </Link>
            <a
              href={hero.ctaSecondary.href}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonVariants({ variant: "secondary", size: "lg" })}
            >
              {hero.ctaSecondary.label}
            </a>
          </div>
        </div>

        {/* Right — the proof: request panel layered over the captured record. */}
        <div className="relative">
          <EndpointCard label={`${hero.request.method} ${hero.request.path}`}>
            {requestText}
          </EndpointCard>

          <Card className="relative z-10 -mt-6 ml-auto w-[88%] shadow-[0_20px_48px_-24px_rgba(14,26,22,0.28)]">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-caption text-steel">
                {hero.captured.meta}
              </span>
              <Badge variant="disliked" dot>
                {hero.captured.rating}
              </Badge>
            </div>
            <p className="mt-3 text-body-md break-keep text-slate">
              {hero.captured.message}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {hero.captured.tags.map((tag) => (
                <Chip key={tag}>{tag}</Chip>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </Section>
  );
}
